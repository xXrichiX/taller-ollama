"""Autorización a nivel de recurso (anti-IDOR / data-level auth)."""

from __future__ import annotations

from fastapi import HTTPException

from api.session import AppSession, require_sucursal
from services import catalog_service, cita_service
from services.user_roles import is_cliente, is_mecanico, is_workshop_staff


def assert_cita_access(session: AppSession, cita: dict) -> None:
  """Verifica que la cita pertenece al usuario según rol y sucursal activa."""
  if not cita:
    raise HTTPException(status_code=404, detail="Cita no encontrada")

  rol = session.user.get("rol_nombre")
  uid = session.user["id"]

  if is_cliente(rol):
    if not session.id_cliente or cita.get("id_cliente") != session.id_cliente:
      raise HTTPException(status_code=403, detail="Cita no permitida")
    return

  if is_mecanico(rol) and not catalog_service.user_is_propietario(uid):
    if cita.get("id_mecanico") != uid:
      raise HTTPException(status_code=403, detail="Solo citas asignadas a ti")
    sid = session.id_sucursal
    if sid and cita.get("id_sucursal") and cita["id_sucursal"] != sid:
      raise HTTPException(status_code=403, detail="Cita fuera de la sucursal activa")
    return

  sid = require_sucursal(session)
  if cita.get("id_sucursal") != sid:
    raise HTTPException(status_code=403, detail="Cita fuera de la sucursal activa")


def assert_cliente_in_sucursal(session: AppSession, id_cliente: int) -> None:
  """Cliente debe tener vehículos o registro en la sucursal activa del staff."""
  if is_cliente(session.user.get("rol_nombre")):
    if session.id_cliente != id_cliente:
      raise HTTPException(status_code=403, detail="Cliente no permitido")
    return

  sid = require_sucursal(session)
  if not catalog_service.cliente_belongs_to_sucursal(id_cliente, sid):
    raise HTTPException(status_code=403, detail="Cliente no pertenece a la sucursal activa")


def require_workshop_staff(session: AppSession) -> None:
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")


def require_list_clientes(session: AppSession) -> None:
  """Solo personal del taller con sucursal activa puede listar clientes."""
  if is_cliente(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  require_workshop_staff(session)
  require_sucursal(session)


def scoped_clientes_filters(session: AppSession) -> dict:
  """Nunca devuelve filtros vacíos para listados de clientes."""
  require_list_clientes(session)
  return {"id_sucursal": require_sucursal(session)}
