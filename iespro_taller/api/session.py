"""Sesión API: estado en memoria indexado por jti del JWT RS256."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import Cookie, Header, HTTPException
import jwt

from api.jwt_tokens import decode_session_token, issue_session_token
from api.security_messages import session_error, setup_required
from config import SESSION_COOKIE_NAME, SESSION_IDLE_SECONDS
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
  created_at: float = field(default_factory=time.time)
  last_activity: float = field(default_factory=time.time)

  def touch(self) -> None:
    self.last_activity = time.time()


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


def purge_expired_sessions() -> None:
  now = time.time()
  expired = [
    token
    for token, session in _sessions.items()
    if now - session.last_activity > SESSION_IDLE_SECONDS
  ]
  for token in expired:
    _sessions.pop(token, None)


def create_session(user: dict[str, Any]) -> tuple[AppSession, str]:
  """Crea sesión en memoria y devuelve (session, jwt)."""
  purge_expired_sessions()
  jti = str(uuid.uuid4())
  session = AppSession(token=jti, user=user, chat=ChatService())
  apply_user_to_session(session, user)
  jwt_str, _ = issue_session_token(
    user_id=int(user["id"]),
    rol=str(user.get("rol_nombre") or ""),
    sucursal_id=session.id_sucursal,
    session_id=jti,
  )
  _sessions[jti] = session
  return session, jwt_str


def get_session(token: str | None) -> AppSession | None:
  if not token:
    return None
  session = _sessions.get(token)
  if not session:
    return None
  if time.time() - session.last_activity > SESSION_IDLE_SECONDS:
    _sessions.pop(token, None)
    return None
  session.touch()
  return session


def delete_session(token: str) -> None:
  _sessions.pop(token, None)


def clear_sessions() -> None:
  _sessions.clear()


def _extract_jwt(
  authorization: str | None,
  x_session_token: str | None,
  cookie_token: str | None = None,
) -> str | None:
  if cookie_token:
    return cookie_token.strip()
  if x_session_token:
    return x_session_token.strip()
  if authorization and authorization.lower().startswith("bearer "):
    return authorization[7:].strip()
  return None


def _session_from_jwt(jwt_token: str | None) -> AppSession | None:
  if not jwt_token:
    return None
  try:
    claims = decode_session_token(jwt_token)
  except jwt.PyJWTError:
    return None
  jti = str(claims.get("jti") or "")
  session = get_session(jti)
  if not session:
    return None
  if str(session.user.get("id")) != str(claims.get("sub")):
    return None
  return session


def require_session(
  authorization: str | None = Header(default=None),
  x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
  session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AppSession:
  purge_expired_sessions()
  session = _session_from_jwt(_extract_jwt(authorization, x_session_token, session_cookie))
  if not session:
    raise HTTPException(status_code=401, detail=session_error())
  return session


def require_sucursal(session: AppSession) -> int:
  if not session.id_sucursal:
    raise HTTPException(status_code=400, detail=setup_required("Selecciona una sucursal activa"))
  return session.id_sucursal


def require_isla(session: AppSession) -> int:
  if not session.id_isla:
    raise HTTPException(status_code=400, detail=setup_required("Selecciona una isla activa"))
  return session.id_isla


def isla_belongs_to_sucursal(id_isla: int, id_sucursal: int) -> bool:
  return any(i["id"] == id_isla for i in cita_service.list_islas(id_sucursal))
