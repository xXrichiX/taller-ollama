"""API HTTP del asistente IESPRO-Taller."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
  sys.path.insert(0, str(BASE))

from config import CORS_ORIGINS  # noqa: E402
from db.init_db import init_database  # noqa: E402
from api.rest_routes import router  # noqa: E402
from api.session import clear_sessions  # noqa: E402


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

app.add_middleware(
  CORSMiddleware,
  allow_origins=CORS_ORIGINS + ["*"] if os.getenv("CORS_ALLOW_ALL") == "1" else CORS_ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/health")
def health():
  from db.connection import test_connection
  ok, msg = test_connection()
  return {"status": "ok" if ok else "degraded", "database": msg}


@app.get("/api/observability/recent")
def observability_recent(limit: int = 20):
  from db.observability_repository import ObservabilityRepository
  repo = ObservabilityRepository()
  repo.ensure_table()
  rows = repo.list_recent(limit=min(limit, 100))
  return {"logs": rows}
