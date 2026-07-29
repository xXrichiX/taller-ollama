"""Perfil de cuenta para el cliente — sin exponer matriz de permisos en producción."""

from __future__ import annotations

from api.session import AppSession
from services import catalog_service, cita_service
from services.user_roles import is_cliente, is_mecanico, is_workshop_staff


def account_profile(session: AppSession) -> str:
  rol = session.user.get("rol_nombre")
  uid = int(session.user["id"])
  if is_cliente(rol):
    return "client"
  if catalog_service.user_is_propietario(uid):
    return "owner"
  if is_mecanico(rol):
    return "mechanic"
  if is_workshop_staff(rol):
    return "staff"
  return "guest"


def account_ui(session: AppSession) -> dict[str, bool]:
  uid = int(session.user["id"])
  rol = session.user.get("rol_nombre")
  es_propietario = catalog_service.user_is_propietario(uid)
  needs_setup = catalog_service.user_needs_taller_setup(uid, rol)
  islas = cita_service.list_islas(session.id_sucursal) if session.id_sucursal else []
  return {
    "isla_picker": len(islas) > 1,
    "workshop_module": is_workshop_staff(rol) and len(islas) > 1,
    "needs_setup": needs_setup,
    "can_add_branch": catalog_service.user_can_create_sucursal(uid),
  }
