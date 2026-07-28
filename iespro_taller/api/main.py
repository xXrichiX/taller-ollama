"""API HTTP del asistente IESPRO-Taller."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
  sys.path.insert(0, str(BASE))

from config import CORS_ORIGINS, IS_PRODUCTION  # noqa: E402
from db.init_db import init_database  # noqa: E402
from api.rest_routes import router  # noqa: E402
from api.session import clear_sessions  # noqa: E402
from api.rate_limit import limiter  # noqa: E402
from api.security_headers import SecurityHeadersMiddleware  # noqa: E402
from api.audit_middleware import AuditAccessMiddleware  # noqa: E402
from api.production_checks import validate_production_config  # noqa: E402
from api.security_messages import bad_request, not_found  # noqa: E402
from api.metrics import PrometheusMiddleware, router as metrics_router  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
  validate_production_config()
  ok, msg = init_database()
  if not ok:
    print(f"[WARN] BD: {msg}")
  try:
    from db.audit_repository import AuditRepository

    repo = AuditRepository()
    repo.ensure_table()
    purged = repo.purge_older_than_retention()
    if purged:
      print(f"[INFO] Auditoría: {purged} registros purgados (retención)")
  except Exception:
    pass
  yield
  clear_sessions()


_docs_kwargs: dict = {}
if IS_PRODUCTION:
  _docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(
  title="IESPRO-Taller API",
  version="2.0.0",
  lifespan=lifespan,
  **_docs_kwargs,
)

app.add_middleware(PrometheusMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuditAccessMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError):
  if IS_PRODUCTION:
    return JSONResponse(
      status_code=422,
      content={"ok": False, "detail": "Los datos proporcionados no son válidos."},
    )
  return JSONResponse(status_code=422, content={"detail": _exc.errors()})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
  if exc.status_code == 403:
    from services import audit_actions as audit
    from services.audit_service import audit_from_request

    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    audit_from_request(
      request,
      accion=audit.ACCESS_DENIED,
      detalle=detail[:120],
      resultado="denied",
    )
  detail = exc.detail
  if IS_PRODUCTION:
    if exc.status_code == 400:
      detail = bad_request(str(detail) if isinstance(detail, str) else "invalid")
    elif exc.status_code == 404:
      detail = not_found(str(detail) if isinstance(detail, str) else "missing")
    elif exc.status_code == 503:
      detail = "Servicio no disponible temporalmente."
  return JSONResponse(status_code=exc.status_code, content={"detail": detail})


_cors_origins = list(CORS_ORIGINS)
if os.getenv("CORS_ALLOW_ALL") == "1" and not IS_PRODUCTION:
  _cors_origins.append("*")

app.add_middleware(
  CORSMiddleware,
  allow_origins=_cors_origins,
  allow_credentials=not IS_PRODUCTION,
  allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allow_headers=["*"],
)

app.include_router(router)
app.include_router(metrics_router)


@app.get("/api/health")
@limiter.limit("120/minute")
def health(request: Request):
  """Liveness público: en producción no expone estado de BD ni versión."""
  headers = {"Cache-Control": "no-store"}
  if IS_PRODUCTION:
    return JSONResponse(content={"status": "ok"}, headers=headers)
  from db.connection import test_connection

  ok, _msg = test_connection()
  return JSONResponse(
    content={"status": "ok" if ok else "degraded"},
    headers=headers,
  )
