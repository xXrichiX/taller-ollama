"""Sesión API: token en memoria + dependencia FastAPI."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import Header, HTTPException

from services import catalog_service, cita_service
from services.chat_service import ChatService
from services.user_roles import is_cliente, is_mecanico, is_workshop_staff

_sessions: dict[str, "AppSession"] = {}


@dataclass
class AppSession:
  token: str
  user: dict[str, Any]
  id_sucursal: int | None = None
  id_isla: int | None = None
  id_cliente: int | None = None
  chat: ChatService = field(default_factory=ChatService)


def _first_isla_id(id_sucursal: int | None) -> int | None:
  if not id_sucursal:
    return None
  islas = cita_service.list_islas(id_sucursal)
  return islas[0]["id"] if islas else None


def user_payload(user: dict[str, Any], session: AppSession | None = None) -> dict[str, Any]:
  return {
    "id": user["id"],
    "nombre": user["nombre"],
    "email": user["email"],
    "rol_nombre": user.get("rol_nombre"),
    "puesto_nombre": user.get("puesto_nombre"),
    "sucursales_ids": user.get("sucursales_ids") or [],
    "id_sucursal": session.id_sucursal if session else user.get("id_sucursal"),
    "id_isla": session.id_isla if session else None,
    "id_cliente": session.id_cliente if session else None,
  }


def _sync_chat_scope(session: AppSession) -> None:
  session.chat.id_sucursal = session.id_sucursal
  session.chat.id_isla = session.id_isla


def apply_user_to_session(session: AppSession, user: dict[str, Any]) -> None:
  session.user = user
  session.id_cliente = None
  sucursales_ids = user.get("sucursales_ids") or []

  if is_cliente(user.get("rol_nombre")) and user.get("id"):
    cliente = catalog_service.get_cliente_by_usuario(user["id"])
    session.id_cliente = cliente["id"] if cliente else None

  if is_mecanico(user.get("rol_nombre")) or (
    is_workshop_staff(user.get("rol_nombre")) and not is_cliente(user.get("rol_nombre"))
  ):
    session.id_sucursal = sucursales_ids[0] if sucursales_ids else user.get("id_sucursal")
  else:
    session.id_sucursal = user.get("id_sucursal")

  if is_workshop_staff(user.get("rol_nombre")) and not is_cliente(user.get("rol_nombre")):
    if session.id_isla is None:
      session.id_isla = _first_isla_id(session.id_sucursal)
  else:
    session.id_isla = None

  _sync_chat_scope(session)
  session.chat.set_user(user)


def create_session(user: dict[str, Any]) -> AppSession:
  token = str(uuid.uuid4())
  session = AppSession(token=token, user=user, chat=ChatService())
  apply_user_to_session(session, user)
  _sessions[token] = session
  return session


def get_session(token: str | None) -> AppSession | None:
  if not token:
    return None
  return _sessions.get(token)


def delete_session(token: str) -> None:
  _sessions.pop(token, None)


def clear_sessions() -> None:
  _sessions.clear()


def _extract_token(authorization: str | None, x_session_token: str | None) -> str | None:
  if x_session_token:
    return x_session_token.strip()
  if authorization and authorization.lower().startswith("bearer "):
    return authorization[7:].strip()
  return None


def require_session(
  authorization: str | None = Header(default=None),
  x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> AppSession:
  session = get_session(_extract_token(authorization, x_session_token))
  if not session:
    raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
  return session


def require_sucursal(session: AppSession) -> int:
  if not session.id_sucursal:
    raise HTTPException(status_code=400, detail="Selecciona una sucursal activa")
  return session.id_sucursal


def require_isla(session: AppSession) -> int:
  if not session.id_isla:
    raise HTTPException(status_code=400, detail="Selecciona una isla activa en la barra superior")
  return session.id_isla


def isla_belongs_to_sucursal(id_isla: int, id_sucursal: int) -> bool:
  return any(i["id"] == id_isla for i in cita_service.list_islas(id_sucursal))
