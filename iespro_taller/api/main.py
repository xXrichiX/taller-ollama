"""API HTTP del asistente IESPRO-Taller (Semana 6)."""

from __future__ import annotations

import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Asegurar imports del paquete iespro_taller
BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
  sys.path.insert(0, str(BASE))

from config import CORS_ORIGINS  # noqa: E402
from db.init_db import init_database  # noqa: E402
from services import catalog_service  # noqa: E402
from services.chat_service import ChatService  # noqa: E402

_sessions: dict[str, ChatService] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
  ok, msg = init_database()
  if not ok:
    print(f"[WARN] BD: {msg}")
  yield
  _sessions.clear()


app = FastAPI(
  title="IESPRO-Taller API",
  version="1.0.0",
  lifespan=lifespan,
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=CORS_ORIGINS + ["*"] if os.getenv("CORS_ALLOW_ALL") == "1" else CORS_ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


class LoginRequest(BaseModel):
  email: str
  password: str


class ChatRequest(BaseModel):
  message: str = Field(..., min_length=1)
  token: str | None = None
  id_sucursal: int | None = None


class BootstrapRequest(BaseModel):
  token: str


def _user_payload(user: dict) -> dict[str, Any]:
  return {
    "id": user["id"],
    "nombre": user["nombre"],
    "email": user["email"],
    "rol_nombre": user.get("rol_nombre"),
    "sucursales_ids": user.get("sucursales_ids") or [],
  }


def _get_chat(token: str) -> ChatService:
  chat = _sessions.get(token)
  if not chat:
    raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
  return chat


@app.get("/api/health")
def health():
  from db.connection import test_connection
  ok, msg = test_connection()
  return {"status": "ok" if ok else "degraded", "database": msg}


@app.post("/api/auth/login")
def login(req: LoginRequest):
  user = catalog_service.login(req.email.strip(), req.password)
  if not user:
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")

  sucursales = user.get("sucursales_ids") or []
  if not sucursales:
    raise HTTPException(status_code=400, detail="Usuario sin sucursal asignada")

  token = str(uuid.uuid4())
  chat = ChatService(id_sucursal=sucursales[0])
  chat.set_user(user)
  _sessions[token] = chat

  return {"token": token, "user": _user_payload(user)}


@app.post("/api/chat")
def chat(req: ChatRequest):
  if not req.token:
    raise HTTPException(status_code=401, detail="Token requerido")

  chat_svc = _get_chat(req.token)
  if req.id_sucursal:
    chat_svc.id_sucursal = req.id_sucursal

  result = chat_svc.ask(req.message.strip())
  return {
    "answer": result.get("answer"),
    "route": result.get("route"),
    "tool_calls": result.get("tool_calls", []),
    "metrics": result.get("metrics", {}),
  }


@app.post("/api/rag/bootstrap")
def rag_bootstrap(req: BootstrapRequest):
  chat_svc = _get_chat(req.token)
  ok, msg = chat_svc.bootstrap()
  return {"ok": ok, "message": msg}


@app.get("/api/observability/recent")
def observability_recent(limit: int = 20):
  from db.observability_repository import ObservabilityRepository
  repo = ObservabilityRepository()
  repo.ensure_table()
  rows = repo.list_recent(limit=min(limit, 100))
  return {"logs": rows}
