"""Validación de sucursal/isla en peticiones del chat (anti-IDOR)."""

from __future__ import annotations

from fastapi import HTTPException

from api.security_messages import forbidden
from api.session import AppSession, isla_belongs_to_sucursal, require_sucursal
from services import catalog_service


def apply_chat_scope(
  session: AppSession,
  *,
  id_sucursal: int | None,
  id_isla: int | None,
) -> None:
  """Aplica sucursal/isla al chat solo si el usuario tiene acceso."""
  if id_sucursal is not None:
    if not catalog_service.user_can_access_sucursal(session.user["id"], id_sucursal):
      raise HTTPException(status_code=403, detail=forbidden("Sucursal no permitida"))
    session.id_sucursal = id_sucursal
    session.chat.id_sucursal = id_sucursal

  if id_isla is not None:
    sid = require_sucursal(session)
    if not isla_belongs_to_sucursal(id_isla, sid):
      raise HTTPException(status_code=403, detail=forbidden("Isla no permitida"))
    session.id_isla = id_isla
    session.chat.id_isla = id_isla
