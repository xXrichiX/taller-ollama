"""API HTTP del asistente IESPRO-Taller."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
  ok, msg = init_database()
  if not ok:
    print(f"[WARN] BD: {msg}")
  yield
  clear_sessions()


app = FastAPI(
  title="IESPRO-Taller API",
  version="2.0.0",
  lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError):
  if IS_PRODUCTION:
    return JSONResponse(
      status_code=422,
      content={"ok": False, "detail": "Los datos proporcionados no son válidos."},
    )
  return JSONResponse(status_code=422, content={"detail": _exc.errors()})


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


@app.get("/api/health")
def health():
  if IS_PRODUCTION:
    return {"status": "ok"}
  from db.connection import test_connection

  ok, _msg = test_connection()
  return {"status": "ok" if ok else "degraded"}
