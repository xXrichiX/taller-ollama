"""Registro de auditoría (login, IA, cambios, errores)."""

from __future__ import annotations

import logging
from typing import Any

from db.audit_repository import AuditRepository

logger = logging.getLogger(__name__)
_repo = AuditRepository()
_table_ready = False


def _ensure() -> None:
  global _table_ready
  if _table_ready:
    return
  try:
    _repo.ensure_table()
    _table_ready = True
  except Exception:
    logger.exception("No se pudo inicializar tabla audit_logs")


def audit(
  *,
  accion: str,
  id_usuario: int | None = None,
  recurso: str | None = None,
  detalle: str | None = None,
  ip: str | None = None,
  user_agent: str | None = None,
  resultado: str = "ok",
) -> None:
  try:
    _ensure()
    _repo.insert(
      id_usuario=id_usuario,
      accion=accion,
      recurso=recurso,
      detalle=detalle,
      ip=ip,
      user_agent=user_agent,
      resultado=resultado,
    )
  except Exception:
    logger.exception("Fallo al registrar auditoría accion=%s", accion)


def audit_session_action(
  request: Any,
  session: Any,
  *,
  accion: str,
  recurso: str | None = None,
  detalle: str | None = None,
  resultado: str = "ok",
) -> None:
  """Registra auditoría con usuario de la sesión activa."""
  user_id = None
  if session is not None and getattr(session, "user", None):
    user_id = session.user.get("id")
  audit_from_request(
    request,
    accion=accion,
    id_usuario=user_id,
    recurso=recurso,
    detalle=detalle,
    resultado=resultado,
  )


def audit_from_request(
  request: Any,
  *,
  accion: str,
  id_usuario: int | None = None,
  recurso: str | None = None,
  detalle: str | None = None,
  resultado: str = "ok",
) -> None:
  ip = None
  ua = None
  if request is not None:
    try:
      from api.client_ip import get_client_ip

      ip = get_client_ip(request)
      ua = request.headers.get("User-Agent", "")
    except Exception:
      pass
  audit(
    accion=accion,
    id_usuario=id_usuario,
    recurso=recurso,
    detalle=detalle,
    ip=ip,
    user_agent=ua,
    resultado=resultado,
  )
