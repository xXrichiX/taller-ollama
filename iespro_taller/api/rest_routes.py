"""Endpoints REST — reemplazo de la UI Tkinter."""

from __future__ import annotations

import json
import queue
import threading
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from api.rate_limit import rate_limit
from api.chat_scope import apply_chat_scope
from api.chat_response import public_chat_messages, public_chat_result
from api.access_checks import (
  assert_cita_access,
  assert_cliente_in_sucursal,
  require_list_clientes,
  scoped_clientes_filters,
)
from api.security_messages import REGISTER_GENERIC_MESSAGE
from api.session_cookies import clear_session_cookie, json_with_session
from api.session import (
  AppSession,
  apply_user_to_session,
  create_session,
  delete_session,
  isla_belongs_to_sucursal,
  require_isla,
  require_session,
  require_sucursal,
  user_payload,
)
from services import catalog_service, cita_service, inventory_service
from config import (
  IS_PRODUCTION,
  MAX_ISLAS_PER_SUCURSAL,
  REGISTRATION_ENABLED,
  REGISTRATION_INVITE_CODE,
  TURNSTILE_SECRET_KEY,
  TURNSTILE_SITE_KEY,
)
from services.turnstile import turnstile_enabled, verify_turnstile
from services.estado_labels import ESTADOS_MECANICO_UI, ESTADOS_UI, estado_a_etiqueta, etiqueta_a_estado
from services.password_policy import normalize_password, validate_password
from services.user_roles import (
  is_cliente,
  is_mecanico,
  is_pending,
  is_workshop_staff,
  role_display_label,
)
from services.audit_service import audit_from_request

router = APIRouter(prefix="/api")


# --- Auth ---


class LoginBody(BaseModel):
  email: str
  password: str


class RegisterBody(BaseModel):
  nombre: str
  email: str
  password: str
  invite_code: str = ""
  captcha_token: str = ""
  captcha_challenge: str = ""
  captcha_answer: str = ""


@router.get("/auth/public-config")
def auth_public_config():
  use_turnstile = bool(TURNSTILE_SECRET_KEY)
  return {
    "registration_enabled": REGISTRATION_ENABLED,
    "turnstile_site_key": TURNSTILE_SITE_KEY if use_turnstile else "",
    "invite_required": bool(REGISTRATION_INVITE_CODE),
    "captcha_mode": "turnstile" if use_turnstile else "none",
  }


@router.get("/auth/captcha")
def auth_captcha():
  """Reservado: CAPTCHA matemático deshabilitado (usar Turnstile si hace falta)."""
  raise HTTPException(status_code=404, detail="No disponible")


def _user_is_propietario(session: AppSession) -> bool:
  return catalog_service.user_is_propietario(session.user["id"])


def _require_propietario(session: AppSession) -> None:
  if not _user_is_propietario(session):
    raise HTTPException(status_code=403, detail="Solo el dueño del taller puede hacer esto")


def _require_sucursal_access(session: AppSession, id_sucursal: int) -> None:
  if not catalog_service.user_can_access_sucursal(session.user["id"], id_sucursal):
    raise HTTPException(status_code=403, detail="Sucursal no permitida")


class SucursalActivaBody(BaseModel):
  id_sucursal: int


class IslaActivaBody(BaseModel):
  id_isla: int


@router.post("/auth/login")
@rate_limit("5/minute")
def auth_login(request: Request, body: LoginBody):
  user = catalog_service.login(body.email.strip(), body.password)
  if not user:
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")
  if is_pending(user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Cuenta pendiente de activación")

  sucursales = user.get("sucursales_ids") or []

  session, jwt_token = create_session(user)
  payload: dict[str, Any] = {
    "user": user_payload(user, session),
    "role_label": role_display_label(
      user.get("rol_nombre"),
      es_propietario=bool(user.get("es_propietario")),
    ),
  }
  if not IS_PRODUCTION:
    payload["token"] = jwt_token
  audit_from_request(
    request,
    accion="auth.login",
    id_usuario=user["id"],
    recurso="session",
    resultado="ok",
  )
  return json_with_session(payload, jwt_token)


@router.post("/auth/register")
@rate_limit("5/minute")
def auth_register(request: Request, body: RegisterBody):
  if not REGISTRATION_ENABLED:
    raise HTTPException(status_code=403, detail="El registro público está deshabilitado.")
  if REGISTRATION_INVITE_CODE and body.invite_code.strip() != REGISTRATION_INVITE_CODE:
    raise HTTPException(status_code=403, detail="Código de invitación inválido.")
  if turnstile_enabled():
    client_ip = request.client.host if request.client else None
    if not verify_turnstile(body.captcha_token, client_ip):
      raise HTTPException(status_code=400, detail="Verificación CAPTCHA fallida.")

  result = catalog_service.register_usuario(
    body.nombre.strip(),
    body.email.strip().lower(),
    normalize_password(body.password),
  )
  if result.get("duplicate"):
    return {"ok": True, "message": REGISTER_GENERIC_MESSAGE}
  if not result.get("ok"):
    raise HTTPException(status_code=400, detail=result.get("error", "No se pudo registrar"))

  return {"ok": True, "message": REGISTER_GENERIC_MESSAGE}


@router.post("/auth/logout")
@rate_limit("30/minute")
def auth_logout(request: Request, session: AppSession = Depends(require_session)):
  audit_from_request(
    request,
    accion="auth.logout",
    id_usuario=session.user["id"],
    recurso="session",
  )
  delete_session(session.token)
  response = JSONResponse(content={"ok": True})
  clear_session_cookie(response)
  return response


@router.get("/speech/status")
def speech_status(session: AppSession = Depends(require_session)):
  from services import speech_service

  available = speech_service.speech_available()
  if IS_PRODUCTION:
    return {"available": available}
  path = speech_service.resolve_model_path()
  return {
    "available": available,
    "model_path": str(path) if path else None,
  }


@router.post("/speech/transcribe")
@rate_limit("20/minute")
async def speech_transcribe(
  request: Request,
  audio: UploadFile = File(...),
  session: AppSession = Depends(require_session),
):
  from services import speech_service

  data = await audio.read()
  if not speech_service.is_allowed_audio_payload(data):
    raise HTTPException(status_code=400, detail="Formato de audio no permitido.")
  try:
    result = speech_service.transcribe_audio(data)
  except Exception:
    raise HTTPException(
      status_code=503,
      detail="Transcripción de voz no disponible. Usa el teclado o configura Vosk.",
    )
  if not result.get("ok"):
    raise HTTPException(status_code=400, detail=result.get("error", "No se pudo transcribir."))
  return {"text": result["text"]}


@router.get("/auth/me")
@rate_limit("60/minute")
def auth_me(request: Request, session: AppSession = Depends(require_session)):
  rol = session.user.get("rol_nombre")
  if catalog_service.user_needs_taller_setup(session.user["id"], rol):
    catalog_service.provision_taller_personal(session.user["id"], session.user.get("nombre", ""))
    user = catalog_service.get_user_by_id(session.user["id"])
    if user:
      session.user.update(user)
      ids = user.get("sucursales_ids") or []
      if ids:
        session.id_sucursal = ids[0]
        session.id_isla = None
        session.chat.id_sucursal = ids[0]
        apply_user_to_session(session, user)
  return {
    "user": user_payload(session.user, session),
    "role_label": role_display_label(
      session.user.get("rol_nombre"),
      es_propietario=catalog_service.user_is_propietario(session.user["id"]),
    ),
    "permissions": _permissions(session),
  }


class PerfilUpdateBody(BaseModel):
  nombre: str
  email: str
  password: str = ""


@router.put("/auth/perfil")
def auth_update_perfil(body: PerfilUpdateBody, session: AppSession = Depends(require_session)):
  result = catalog_service.update_usuario_perfil(
    session.user["id"],
    body.nombre.strip(),
    body.email.strip(),
    normalize_password(body.password) if body.password.strip() else None,
  )
  if not result.get("ok"):
    raise HTTPException(status_code=400, detail=result.get("error", "No se pudo actualizar"))
  user = catalog_service.get_user_by_id(session.user["id"])
  if user:
    session.user.update(user)
  return {
    "ok": True,
    "user": user_payload(session.user, session),
  }


@router.put("/session/sucursal")
def set_sucursal(body: SucursalActivaBody, session: AppSession = Depends(require_session)):
  allowed = session.user.get("sucursales_ids") or []
  if body.id_sucursal not in allowed:
    raise HTTPException(status_code=403, detail="Sucursal no permitida")
  session.id_sucursal = body.id_sucursal
  session.id_isla = None
  apply_user_to_session(session, session.user)
  return {"ok": True, "id_sucursal": body.id_sucursal, "id_isla": session.id_isla}


@router.put("/session/isla")
def set_isla(body: IslaActivaBody, session: AppSession = Depends(require_session)):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  if not isla_belongs_to_sucursal(body.id_isla, id_sucursal):
    raise HTTPException(status_code=403, detail="Isla no permitida")
  session.id_isla = body.id_isla
  session.chat.id_isla = body.id_isla
  return {"ok": True, "id_isla": body.id_isla}


@router.get("/islas")
def list_islas_activas(session: AppSession = Depends(require_session)):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  islas = cita_service.list_islas(id_sucursal)
  for i in islas:
    i["activo_label"] = "Sí" if i.get("activo", 1) else "No"
  return {"islas": islas, "id_isla_activa": session.id_isla}


def _permissions(session: AppSession) -> dict[str, bool]:
  rol = session.user.get("rol_nombre")
  uid = session.user["id"]
  es_propietario = catalog_service.user_is_propietario(uid)
  needs_setup = catalog_service.user_needs_taller_setup(uid, rol)
  can_create_sucursal = catalog_service.user_can_create_sucursal(uid)
  islas = cita_service.list_islas(session.id_sucursal) if session.id_sucursal else []
  return {
    "is_admin": False,
    "is_propietario": es_propietario,
    "is_mecanico": is_mecanico(rol),
    "is_cliente": is_cliente(rol),
    "is_staff": is_workshop_staff(rol),
    "needs_taller_setup": needs_setup,
    "can_create_sucursal": can_create_sucursal,
    "can_manage_branch": es_propietario,
    "can_manage_citas": is_workshop_staff(rol) and not needs_setup,
    "can_create_citas": (es_propietario or is_mecanico(rol) or is_cliente(rol)) and not needs_setup,
    "can_manage_usuarios": False,
    "show_isla_picker": len(islas) > 1,
    "show_taller_module": is_workshop_staff(rol) and len(islas) > 1,
  }


def _requires_sucursal(session: AppSession) -> bool:
  rol = session.user.get("rol_nombre")
  return bool(is_workshop_staff(rol) and not session.id_sucursal)


# --- Dashboard ---

_ACTIVE_ESTADOS = ("EN_PROCESO", "EN_REPARACION", "DIAGNOSTICO")
_PENDING_ESTADOS = ("PENDIENTE", "RECIBIDO")


def _format_fecha_cita(fecha_cita) -> tuple[str, str]:
  if not fecha_cita:
    return "—", "—"
  s = str(fecha_cita)
  if " " in s:
    date_part, time_part = s.split(" ", 1)
    hora = time_part[:5] if len(time_part) >= 5 else time_part
    parts = date_part.split("-")
    if len(parts) == 3:
      fecha = f"{parts[2]}/{parts[1]}/{parts[0]}"
    else:
      fecha = date_part
    return hora, fecha
  return "—", s[:10]


def _cita_dashboard_row(c: dict) -> dict:
  hora, fecha = _format_fecha_cita(c.get("fecha_cita"))
  veh_parts = [p for p in (c.get("placa"), c.get("modelo")) if p]
  return {
    "id": c["id"],
    "hora": hora,
    "fecha_programada": fecha,
    "cliente": c.get("cliente"),
    "vehiculo": " ".join(veh_parts) if veh_parts else "—",
    "estado": estado_a_etiqueta(c.get("estado")),
    "mecanico": c.get("mecanico"),
    "servicio": (c.get("descripcion_fallo") or "")[:60],
  }


@router.get("/dashboard")
def dashboard(session: AppSession = Depends(require_session)):
  empty = {
    "title": "Resumen del taller",
    "stats": {},
    "islas_ocupadas": 0,
    "islas_total": 0,
    "mecanicos_ocupados": 0,
    "mecanicos_total": 0,
    "recent_citas": [],
    "pending_citas": [],
    "ordenes": [],
  }
  if _requires_sucursal(session):
    return empty

  rol = session.user.get("rol_nombre")
  stats: dict[str, int] = {}
  citas_filters = _citas_filters(session)
  es_propietario = catalog_service.user_is_propietario(session.user["id"])

  citas = cita_service.list_citas(**citas_filters)
  pendientes = sum(1 for c in citas if c.get("estado") in _PENDING_ESTADOS)
  en_proceso = sum(1 for c in citas if c.get("estado") in _ACTIVE_ESTADOS)
  completadas = sum(1 for c in citas if c.get("estado") in ("COMPLETADA", "FINALIZADO"))

  islas_ocupadas = 0
  islas_total = 0
  mecanicos_ocupados = 0
  mecanicos_total = 0

  if is_cliente(rol):
    vehiculos = cita_service.list_vehiculos(id_cliente=session.id_cliente)
    stats = {
      "vehiculos": len(vehiculos),
      "citas": len(citas),
      "pendientes": pendientes,
      "en_proceso": en_proceso,
      "completadas": completadas,
    }
  elif is_mecanico(rol) and not es_propietario:
    stats = {
      "citas": len(citas),
      "pendientes": pendientes,
      "en_proceso": en_proceso,
      "completadas": completadas,
    }
  else:
    clientes = catalog_service.list_clientes(id_sucursal=session.id_sucursal)
    vehiculos = cita_service.list_vehiculos(id_sucursal=session.id_sucursal)
    islas = cita_service.list_islas(session.id_sucursal)
    mecanicos = cita_service.list_mecanicos(session.id_sucursal)
    stats = {
      "clientes": len(clientes),
      "vehiculos": len(vehiculos),
      "citas": len(citas),
      "pendientes": pendientes,
      "en_proceso": en_proceso,
      "completadas": completadas,
      "islas": len(islas),
      "mecanicos": len(mecanicos),
    }
    islas_total = len(islas)
    islas_ocupadas = len({
      c["id_isla"] for c in citas
      if c.get("estado") in _ACTIVE_ESTADOS and c.get("id_isla")
    })
    mecanicos_total = len(mecanicos)
    mecanicos_ocupados = len({
      c["id_mecanico"] for c in citas
      if c.get("estado") in _ACTIVE_ESTADOS and c.get("id_mecanico")
    })

  pending_source = [c for c in citas if c.get("estado") in _PENDING_ESTADOS]
  pending_source.sort(key=lambda c: str(c.get("fecha_cita") or ""))
  ordenes = [_cita_dashboard_row(c) for c in citas[:24]]

  title = "Resumen del taller"
  if is_cliente(rol):
    title = "Mi resumen"
  elif is_mecanico(rol) and not es_propietario:
    title = "Panel del mecánico"
  elif es_propietario:
    title = "Mi taller"

  return {
    "title": title,
    "stats": stats,
    "islas_ocupadas": islas_ocupadas,
    "islas_total": islas_total,
    "mecanicos_ocupados": mecanicos_ocupados,
    "mecanicos_total": mecanicos_total,
    "ordenes": ordenes,
    "citas_lista": ordenes,
  }


def _citas_filters(session: AppSession) -> dict[str, Any]:
  filters: dict[str, Any] = {}
  if is_cliente(session.user.get("rol_nombre")) and session.id_cliente:
    filters["id_cliente"] = session.id_cliente
  if session.id_sucursal:
    filters["id_sucursal"] = session.id_sucursal
  if session.id_isla and is_workshop_staff(session.user.get("rol_nombre")):
    filters["id_isla"] = session.id_isla
  return filters


def _clientes_filters(session: AppSession) -> dict[str, Any]:
  if session.id_sucursal:
    return {"id_sucursal": session.id_sucursal}
  if is_mecanico(session.user.get("rol_nombre")):
    return {"id_mecanico": session.user["id"]}
  return {}


# --- Sucursales ---


class SucursalCreate(BaseModel):
  nombre: str
  direccion: str = ""


class IslaCreate(BaseModel):
  nombre: str
  id_mecanico: int | None = None


@router.get("/sucursales")
def list_sucursales(session: AppSession = Depends(require_session)):
  rows = catalog_service.list_sucursales_usuario(session.user["id"])
  for r in rows:
    r["activo_label"] = "Sí" if r.get("activo", 1) else "No"
  return {"sucursales": rows}


@router.post("/sucursales")
@rate_limit("10/minute")
def create_sucursal(
  request: Request,
  body: SucursalCreate,
  session: AppSession = Depends(require_session),
):
  uid = session.user["id"]
  if not catalog_service.user_can_create_sucursal(uid):
    raise HTTPException(status_code=403, detail="No puedes crear más sucursales")
  nombre = body.nombre.strip()
  if not nombre:
    raise HTTPException(status_code=400, detail="Nombre requerido")
  id_sucursal = catalog_service.create_sucursal(
    nombre,
    body.direccion.strip(),
    id_propietario=uid,
  )
  catalog_service.add_usuario_sucursal(uid, id_sucursal)
  from db.connection import execute

  execute(
    "UPDATE usuarios SET id_sucursal = %s WHERE id = %s AND id_sucursal IS NULL",
    (id_sucursal, uid),
  )
  cita_service.get_mi_taller(id_sucursal)
  ids = list(session.user.get("sucursales_ids") or [])
  if id_sucursal not in ids:
    ids.append(id_sucursal)
    session.user["sucursales_ids"] = ids
  session.id_sucursal = id_sucursal
  session.chat.id_sucursal = id_sucursal
  session.user["es_propietario"] = True
  return {"ok": True, "id": id_sucursal}


@router.get("/sucursales/{id_sucursal}/islas")
def list_islas(id_sucursal: int, session: AppSession = Depends(require_session)):
  _require_sucursal_access(session, id_sucursal)
  rows = cita_service.list_islas(id_sucursal)
  for r in rows:
    r["activo_label"] = "Sí" if r.get("activo", 1) else "No"
  return {"islas": rows}


@router.post("/sucursales/{id_sucursal}/islas")
@rate_limit("15/minute")
def create_isla(
  request: Request,
  id_sucursal: int,
  body: IslaCreate,
  session: AppSession = Depends(require_session),
):
  _require_sucursal_access(session, id_sucursal)
  if not catalog_service.user_owns_sucursal(session.user["id"], id_sucursal):
    raise HTTPException(status_code=403, detail="Solo el dueño puede crear islas")
  if cita_service.count_islas(id_sucursal) >= MAX_ISLAS_PER_SUCURSAL:
    raise HTTPException(status_code=403, detail="Límite de islas alcanzado para esta sucursal")
  nombre = body.nombre.strip()
  if not nombre:
    raise HTTPException(status_code=400, detail="Nombre de isla requerido")
  id_isla = cita_service.create_isla(nombre, id_sucursal)
  if body.id_mecanico:
    cita_service.assign_mecanico_isla(id_isla, body.id_mecanico)
  return {"ok": True, "id": id_isla}


# --- Catálogos ---


@router.get("/catalogos/marcas")
def catalog_marcas(session: AppSession = Depends(require_session)):
  return {"items": catalog_service.list_marcas()}


@router.get("/catalogos/combustibles")
def catalog_combustibles(session: AppSession = Depends(require_session)):
  return {"items": catalog_service.list_tipos_combustible()}


@router.get("/catalogos/unidades")
def catalog_unidades(session: AppSession = Depends(require_session)):
  return {"items": catalog_service.list_tipos_unidad()}


@router.get("/catalogos/puestos")
def catalog_puestos(session: AppSession = Depends(require_session)):
  _require_propietario(session)
  return {"items": catalog_service.list_puestos()}


@router.get("/catalogos/mantenimiento")
def catalog_mantenimiento(session: AppSession = Depends(require_session)):
  id_sucursal = require_sucursal(session)
  return {"items": catalog_service.list_tipos_mantenimiento(id_sucursal)}


# --- Servicios (tipos de mantenimiento) ---


class ServicioCreate(BaseModel):
  nombre: str
  descripcion: str = ""
  precio: float = 0


class ServicioUpdate(BaseModel):
  nombre: str
  descripcion: str = ""
  precio: float = 0


@router.get("/servicios")
def list_servicios(session: AppSession = Depends(require_session)):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  items = catalog_service.list_tipos_mantenimiento(id_sucursal)
  for row in items:
    row["precio"] = float(row.get("precio") or 0)
  return {"items": items}


@router.post("/servicios")
@rate_limit("20/minute")
def create_servicio(
  request: Request,
  body: ServicioCreate,
  session: AppSession = Depends(require_session),
):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  nombre = body.nombre.strip()
  if not nombre:
    raise HTTPException(status_code=400, detail="Nombre requerido")
  if body.precio < 0:
    raise HTTPException(status_code=400, detail="El precio no puede ser negativo")
  id_item = catalog_service.create_tipo_mantenimiento(
    nombre,
    body.descripcion.strip(),
    body.precio,
    id_sucursal,
  )
  return {"ok": True, "id": id_item}


@router.patch("/servicios/{id_servicio}")
def update_servicio(
  id_servicio: int,
  body: ServicioUpdate,
  session: AppSession = Depends(require_session),
):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  nombre = body.nombre.strip()
  if not nombre:
    raise HTTPException(status_code=400, detail="Nombre requerido")
  if body.precio < 0:
    raise HTTPException(status_code=400, detail="El precio no puede ser negativo")
  result = catalog_service.update_tipo_mantenimiento(
    id_servicio,
    id_sucursal,
    nombre,
    body.descripcion.strip(),
    body.precio,
  )
  if not result.get("ok"):
    raise HTTPException(status_code=404, detail=result.get("error", "No encontrado"))
  return {"ok": True}


@router.get("/catalogos/estados-cita")
def catalog_estados(session: AppSession = Depends(require_session)):
  if is_mecanico(session.user.get("rol_nombre")):
    return {"items": ESTADOS_MECANICO_UI}
  return {"items": ESTADOS_UI}


@router.get("/catalogos/mecanicos")
def catalog_mecanicos(
  session: AppSession = Depends(require_session),
  id_sucursal: int | None = None,
):
  sid = id_sucursal if id_sucursal is not None else require_sucursal(session)
  if id_sucursal is not None:
    _require_sucursal_access(session, id_sucursal)
  return {"items": cita_service.list_mecanicos(sid)}


# --- Clientes ---


class ClienteCreate(BaseModel):
  nombre: str
  telefono: str = ""
  email: str = ""


@router.get("/clientes")
@rate_limit("60/minute")
def list_clientes(request: Request, session: AppSession = Depends(require_session)):
  rows = catalog_service.list_clientes(**scoped_clientes_filters(session))
  return {"clientes": rows}


@router.post("/clientes")
@rate_limit("30/minute")
def create_cliente(
  request: Request,
  body: ClienteCreate,
  session: AppSession = Depends(require_session),
):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  nombre = body.nombre.strip()
  telefono = body.telefono.strip()
  email = body.email.strip()
  if len(nombre) < 2:
    raise HTTPException(status_code=400, detail="Indica el nombre del cliente.")
  if telefono and (len(telefono) < 7 or not any(ch.isdigit() for ch in telefono)):
    raise HTTPException(status_code=400, detail="Teléfono inválido. Usa solo números.")
  if email and ("@" not in email or "." not in email.split("@")[-1]):
    raise HTTPException(status_code=400, detail="Correo inválido.")
  id_cliente = catalog_service.create_cliente(
    nombre,
    telefono,
    email,
    None,
    id_sucursal,
  )
  audit_from_request(
    request,
    accion="cliente.create",
    id_usuario=session.user["id"],
    recurso=f"cliente:{id_cliente}",
    detalle=nombre[:120],
  )
  return {"ok": True, "id": id_cliente}


# --- Inventario ---


class InventarioCreate(BaseModel):
  codigo: str = ""
  nombre: str
  descripcion: str = ""
  cantidad: float = 0
  stock_minimo: float = 0
  precio_unitario: float = 0
  unidad: str = "pza"


class InventarioUpdate(BaseModel):
  codigo: str = ""
  nombre: str
  descripcion: str = ""
  cantidad: float
  stock_minimo: float = 0
  precio_unitario: float = 0
  unidad: str = "pza"


class InventarioUpdateMecanico(BaseModel):
  nombre: str
  descripcion: str = ""
  unidad: str = "pza"


class InventarioAjuste(BaseModel):
  delta: float


@router.get("/inventario")
def list_inventario(session: AppSession = Depends(require_session)):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  if _requires_sucursal(session):
    return {"items": []}
  id_isla = require_isla(session)
  return {"items": inventory_service.list_inventario(id_isla)}


@router.post("/inventario")
@rate_limit("30/minute")
def create_inventario(
  request: Request,
  body: InventarioCreate,
  session: AppSession = Depends(require_session),
):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  id_isla = require_isla(session)
  nombre = body.nombre.strip()
  if not nombre:
    raise HTTPException(status_code=400, detail="Nombre requerido")
  payload = body.model_dump()
  if not _user_is_propietario(session):
    payload["precio_unitario"] = 0
    payload["stock_minimo"] = body.stock_minimo if body.stock_minimo >= 0 else 0
  if payload["cantidad"] < 0 or payload["stock_minimo"] < 0 or payload["precio_unitario"] < 0:
    raise HTTPException(status_code=400, detail="Cantidades y precios no pueden ser negativos")
  id_item = inventory_service.create_item(id_sucursal, id_isla, payload)
  return {"ok": True, "id": id_item}


@router.patch("/inventario/{id_item}")
def update_inventario(
  id_item: int,
  body: InventarioUpdate,
  session: AppSession = Depends(require_session),
):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_sucursal = require_sucursal(session)
  id_isla = require_isla(session)

  existing = inventory_service.get_item(id_item, id_isla)
  if not existing:
    raise HTTPException(status_code=404, detail="Artículo no encontrado")

  if _user_is_propietario(session):
    nombre = body.nombre.strip()
    if not nombre:
      raise HTTPException(status_code=400, detail="Nombre requerido")
    if body.cantidad < 0 or body.stock_minimo < 0 or body.precio_unitario < 0:
      raise HTTPException(status_code=400, detail="Cantidades y precios no pueden ser negativos")
    payload = body.model_dump()
  else:
    mec = InventarioUpdateMecanico(
      nombre=body.nombre,
      descripcion=body.descripcion,
      unidad=body.unidad,
    )
    nombre = mec.nombre.strip()
    if not nombre:
      raise HTTPException(status_code=400, detail="Nombre requerido")
    payload = {
      **existing,
      "nombre": nombre,
      "descripcion": mec.descripcion,
      "unidad": mec.unidad,
    }

  result = inventory_service.update_item(id_item, id_isla, payload)
  if not result.get("ok"):
    raise HTTPException(status_code=404, detail=result.get("error", "No encontrado"))
  return {"ok": True}


@router.post("/inventario/{id_item}/ajustar")
def ajustar_inventario(
  id_item: int,
  body: InventarioAjuste,
  session: AppSession = Depends(require_session),
):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  if not _user_is_propietario(session):
    raise HTTPException(status_code=403, detail="Solo el dueño del taller puede ajustar stock")
  id_isla = require_isla(session)
  if body.delta == 0:
    raise HTTPException(status_code=400, detail="Indica cuánto sumar o restar")
  result = inventory_service.ajustar_stock(id_item, id_isla, body.delta)
  if not result.get("ok"):
    raise HTTPException(status_code=400, detail=result.get("error", "No se pudo ajustar"))
  return result


# --- Vehículos ---


class VehiculoCreate(BaseModel):
  numero_economico: str = ""
  placa: str
  serie: str = ""
  modelo: str = ""
  kilometraje: int = 0
  dias_mantenimiento: int = 90
  observaciones: str | None = None
  id_cliente: int | None = None
  id_mecanico_asignado: int | None = None
  id_marca: int
  id_tipo_combustible: int
  id_tipo_unidad: int


@router.get("/vehiculos")
@rate_limit("60/minute")
def list_vehiculos(
  request: Request,
  id_cliente: int | None = None,
  session: AppSession = Depends(require_session),
):
  if _requires_sucursal(session) and not is_cliente(session.user.get("rol_nombre")):
    return {"vehiculos": []}

  rol = session.user.get("rol_nombre")
  if id_cliente and is_workshop_staff(rol):
    assert_cliente_in_sucursal(session, id_cliente)
    rows = cita_service.list_vehiculos(id_cliente=id_cliente, id_sucursal=require_sucursal(session))
  elif is_cliente(rol):
    rows = cita_service.list_vehiculos(id_cliente=session.id_cliente)
  elif is_mecanico(rol):
    rows = cita_service.list_vehiculos(id_mecanico_asignado=session.user["id"])
  else:
    rows = cita_service.list_vehiculos(id_sucursal=session.id_sucursal)
  return {"vehiculos": rows}


@router.post("/vehiculos")
def create_vehiculo(body: VehiculoCreate, session: AppSession = Depends(require_session)):
  id_sucursal = require_sucursal(session)
  rol = session.user.get("rol_nombre")

  if is_cliente(rol):
    if not session.id_cliente:
      raise HTTPException(status_code=400, detail="Ficha de cliente no encontrada")
    id_cliente = session.id_cliente
    id_mecanico = None
  else:
    if not body.id_cliente:
      raise HTTPException(status_code=400, detail="Cliente requerido")
    id_cliente = body.id_cliente
    if is_mecanico(rol):
      id_mecanico = session.user["id"]
    else:
      id_mecanico = body.id_mecanico_asignado

  id_usuario = catalog_service.ensure_cliente_usuario(id_cliente)
  vid = cita_service.create_vehiculo({
    "numero_economico": body.numero_economico.strip(),
    "placa": body.placa.strip(),
    "serie": body.serie.strip(),
    "modelo": body.modelo.strip(),
    "kilometraje": body.kilometraje,
    "dias_mantenimiento": body.dias_mantenimiento,
    "observaciones": body.observaciones,
    "id_cliente": id_cliente,
    "id_usuario": id_usuario,
    "id_sucursal": id_sucursal,
    "id_mecanico_asignado": id_mecanico,
    "id_marca": body.id_marca,
    "id_tipo_combustible": body.id_tipo_combustible,
    "id_tipo_unidad": body.id_tipo_unidad,
  })
  try:
    session.chat.rag.sync_fallas_from_db()
  except Exception:
    pass
  return {"ok": True, "id": vid}


# --- Citas ---


class CitaCreate(BaseModel):
  id_cliente: int | None = None
  id_vehiculo: int
  fecha_cita: str
  hora_cita: str = "09:00"
  descripcion_fallo: str
  fecha_compromiso: str
  hora_compromiso: str = "18:00:00"
  id_mecanico: int | None = None
  id_isla: int | None = None
  servicio_ids: list[int] = Field(default_factory=list)


class CitaUpdate(BaseModel):
  estado: str | None = None
  id_mecanico: int | None = None
  id_isla: int | None = None
  diagnostico: str | None = None
  observaciones: str | None = None
  solucion: str | None = None


def _normalize_hora(hora: str) -> str:
  hora = (hora or "").strip()
  if not hora:
    raise ValueError("Hora requerida")
  parts = hora.split(":")
  if len(parts) == 2:
    h, m = int(parts[0]), int(parts[1])
    return f"{h:02d}:{m:02d}:00"
  if len(parts) == 3:
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    return f"{h:02d}:{m:02d}:{s:02d}"
  raise ValueError("Hora inválida")


@router.get("/citas")
def list_citas(session: AppSession = Depends(require_session)):
  if _requires_sucursal(session):
    return {"citas": []}
  rows = cita_service.list_citas(**_citas_filters(session))
  for r in rows:
    r["fecha_cita"] = str(r.get("fecha_cita", ""))
    r["descripcion_fallo"] = (r.get("descripcion_fallo") or "")[:80]
    r["estado_label"] = estado_a_etiqueta(r.get("estado"))
  return {"citas": rows}


@router.get("/citas/{id_cita}")
@rate_limit("60/minute")
def get_cita(request: Request, id_cita: int, session: AppSession = Depends(require_session)):
  cita = cita_service.get_cita_by_id(id_cita)
  if not cita:
    raise HTTPException(status_code=404, detail="Cita no encontrada")
  assert_cita_access(session, cita)
  falla = cita_service.get_falla_por_cita(id_cita)
  cita["estado_label"] = estado_a_etiqueta(cita.get("estado"))
  return {"cita": cita, "falla": falla}


@router.post("/citas")
def create_cita(body: CitaCreate, session: AppSession = Depends(require_session)):
  id_sucursal = require_sucursal(session)
  rol = session.user.get("rol_nombre")

  if len(body.descripcion_fallo.strip()) < 3:
    raise HTTPException(status_code=400, detail="Describe el fallo (mínimo 3 caracteres)")
  if not body.servicio_ids:
    raise HTTPException(status_code=400, detail="Selecciona tipos de mantenimiento")

  hora = _normalize_hora(body.hora_cita)
  fecha_cita = f"{body.fecha_cita.strip()} {hora}"

  if is_cliente(rol):
    if not session.id_cliente:
      raise HTTPException(status_code=400, detail="Cliente no encontrado")
    defaults = cita_service.get_default_asignacion_taller(id_sucursal)
    id_cliente = session.id_cliente
    id_mecanico = defaults["id_mecanico"]
    id_isla = defaults["id_isla"]
  elif is_workshop_staff(rol):
    id_cliente = body.id_cliente
    if not id_cliente:
      raise HTTPException(status_code=400, detail="Cliente requerido")
    id_mecanico = session.user["id"]
    id_isla = session.id_isla
    if not id_isla:
      raise HTTPException(status_code=400, detail="Selecciona una isla activa en la barra superior")
  else:
    if not body.id_cliente or not body.id_mecanico or not body.id_isla:
      raise HTTPException(status_code=400, detail="Cliente, mecánico e isla requeridos")
    id_cliente = body.id_cliente
    id_mecanico = body.id_mecanico
    id_isla = body.id_isla

  cita_id = cita_service.create_cita({
    "id_cliente": id_cliente,
    "id_vehiculo": body.id_vehiculo,
    "id_sucursal": id_sucursal,
    "fecha_cita": fecha_cita,
    "id_horario": None,
    "id_mecanico": id_mecanico,
    "id_isla": id_isla,
    "descripcion_fallo": body.descripcion_fallo.strip(),
    "fecha_compromiso": body.fecha_compromiso.strip(),
    "hora_compromiso": body.hora_compromiso.strip(),
  }, body.servicio_ids)

  try:
    session.chat.rag.sync_fallas_from_db()
  except Exception:
    pass
  return {"ok": True, "id": cita_id}


@router.patch("/citas/{id_cita}")
def update_cita(id_cita: int, body: CitaUpdate, session: AppSession = Depends(require_session)):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")

  cita = cita_service.get_cita_by_id(id_cita)
  if not cita:
    raise HTTPException(status_code=404, detail="Cita no encontrada")
  assert_cita_access(session, cita)

  es_prop = _user_is_propietario(session)
  if is_mecanico(session.user.get("rol_nombre")) and not es_prop:
    if cita.get("id_mecanico") != session.user["id"]:
      raise HTTPException(status_code=403, detail="Solo citas asignadas a ti")

  estado_raw = etiqueta_a_estado(body.estado) if body.estado else None
  if body.estado and not estado_raw:
    raise HTTPException(status_code=400, detail="Estado inválido")

  if estado_raw == "CANCELADA":
    if not es_prop:
      raise HTTPException(status_code=403, detail="Solo el dueño puede cancelar")
    result = cita_service.cambiar_estado_cita(id_cita, estado_raw)
  elif es_prop:
    updates: dict[str, Any] = {}
    if estado_raw and estado_raw != "CANCELADA":
      updates["estado"] = estado_raw
    if body.id_mecanico is not None:
      updates["id_mecanico"] = body.id_mecanico
    if body.id_isla is not None:
      updates["id_isla"] = body.id_isla
    result = cita_service.update_cita(id_cita, updates) if updates else {"ok": True}
  elif is_mecanico(session.user.get("rol_nombre")):
    if not estado_raw:
      raise HTTPException(status_code=400, detail="Estado requerido")
    result = cita_service.cambiar_estado_cita(id_cita, estado_raw)
  else:
    result = {"ok": True}

  if body.diagnostico or body.observaciones or body.solucion:
    falla_res = cita_service.actualizar_falla_cita(
      id_cita,
      diagnostico=body.diagnostico,
      observaciones=body.observaciones,
      solucion=body.solucion,
    )
    if not falla_res.get("ok"):
      raise HTTPException(status_code=400, detail=falla_res.get("error", "Error al guardar falla"))

  if not result.get("ok"):
    raise HTTPException(status_code=400, detail=result.get("error", "No se pudo actualizar"))

  try:
    session.chat.rag.sync_fallas_from_db()
  except Exception:
    pass
  return {"ok": True}


@router.get("/citas/default-asignacion")
def cita_defaults(session: AppSession = Depends(require_session)):
  id_sucursal = require_sucursal(session)
  return cita_service.get_default_asignacion_taller(id_sucursal)


# --- Usuarios ---


class UsuarioCreate(BaseModel):
  nombre: str
  email: str
  password: str
  id_puesto: int
  puesto_nombre: str
  sucursales_ids: list[int] = Field(default_factory=list)


class UsuarioStaffUpdate(BaseModel):
  id_puesto: int
  puesto_nombre: str
  sucursales_ids: list[int] = Field(default_factory=list)


@router.get("/usuarios")
def list_usuarios(session: AppSession = Depends(require_session)):
  _require_propietario(session)
  if _requires_sucursal(session):
    return {"usuarios": []}
  rows = catalog_service.list_usuarios(session.id_sucursal)
  for r in rows:
    r["puesto"] = r.get("puesto") or "—"
  return {"usuarios": rows}


@router.get("/usuarios/{id_usuario}/sucursales")
def usuario_sucursales(id_usuario: int, session: AppSession = Depends(require_session)):
  _require_propietario(session)
  return {"sucursales": catalog_service.list_sucursales_usuario(id_usuario)}


@router.post("/usuarios")
def create_usuario(body: UsuarioCreate, session: AppSession = Depends(require_session)):
  _require_propietario(session)

  password = normalize_password(body.password)
  ok, msg = validate_password(password, body.email)
  if not ok:
    raise HTTPException(status_code=400, detail=msg)

  puesto = body.puesto_nombre.strip().lower()
  if puesto == "mecánico" and not body.sucursales_ids:
    raise HTTPException(status_code=400, detail="Selecciona sucursales para mecánico")

  id_usuario = catalog_service.create_usuario({
    "nombre": body.nombre.strip(),
    "email": body.email.strip(),
    "password": password,
    "puesto_nombre": body.puesto_nombre.strip(),
    "id_sucursal": body.sucursales_ids[0] if body.sucursales_ids else None,
    "id_puesto": body.id_puesto,
  })
  if body.sucursales_ids and puesto == "mecánico":
    catalog_service.set_usuario_sucursales(id_usuario, body.sucursales_ids)
  return {"ok": True, "id": id_usuario}


@router.patch("/usuarios/{id_usuario}/staff")
def update_usuario_staff(
  id_usuario: int,
  body: UsuarioStaffUpdate,
  session: AppSession = Depends(require_session),
):
  _require_propietario(session)

  puesto = body.puesto_nombre.strip().lower()
  if puesto == "mecánico" and not body.sucursales_ids:
    raise HTTPException(status_code=400, detail="Selecciona sucursales para mecánico")

  catalog_service.assign_usuario_staff(
    id_usuario,
    body.id_puesto,
    body.puesto_nombre.strip(),
    id_sucursales=body.sucursales_ids or None,
  )
  return {"ok": True}


# --- Chat ---


class ChatMessageBody(BaseModel):
  message: str = Field(..., min_length=1)
  id_sucursal: int | None = None
  id_isla: int | None = None


class TokenBody(BaseModel):
  token: str


@router.post("/rag/bootstrap")
@rate_limit("5/minute")
def rag_bootstrap(request: Request, session: AppSession = Depends(require_session)):
  _require_propietario(session)
  ok, msg = session.chat.bootstrap()
  return {"ok": ok, "message": msg}


@router.get("/health/detail")
def health_detail(session: AppSession = Depends(require_session)):
  """Detalle de BD; en producción solo dueño del taller."""
  if IS_PRODUCTION:
    _require_propietario(session)
  from db.connection import test_connection

  ok, msg = test_connection()
  return {"status": "ok" if ok else "degraded", "database": msg}


@router.get("/observability/recent")
def observability_recent(
  limit: int = 20,
  session: AppSession = Depends(require_session),
):
  _require_propietario(session)
  from db.observability_repository import ObservabilityRepository

  repo = ObservabilityRepository()
  repo.ensure_table()
  rows = repo.list_recent(limit=min(limit, 100))
  return {"logs": rows}


@router.get("/audit/recent")
@rate_limit("30/minute")
def audit_recent(
  request: Request,
  limit: int = 50,
  session: AppSession = Depends(require_session),
):
  _require_propietario(session)
  from db.audit_repository import AuditRepository

  repo = AuditRepository()
  repo.ensure_table()
  return {"logs": repo.list_recent(limit=min(limit, 200))}


@router.get("/chat/conversations")
def chat_conversations(session: AppSession = Depends(require_session)):
  require_sucursal(session)
  return {"conversations": session.chat.list_conversations()}


@router.post("/chat/conversations")
@rate_limit("20/minute")
def chat_new_conversation(request: Request, session: AppSession = Depends(require_session)):
  require_sucursal(session)
  conv_id = session.chat.start_new_conversation()
  if not conv_id:
    raise HTTPException(status_code=400, detail="No se pudo crear la conversación")
  return {"ok": True, "id": conv_id}


@router.post("/chat/conversations/{id_conv}/activate")
def chat_activate(id_conv: int, session: AppSession = Depends(require_session)):
  require_sucursal(session)
  ok = session.chat.switch_conversation(id_conv)
  if not ok:
    raise HTTPException(status_code=404, detail="Conversación no encontrada")
  return {"ok": True}


@router.delete("/chat/conversations/{id_conv}")
def chat_delete_conversation(id_conv: int, session: AppSession = Depends(require_session)):
  require_sucursal(session)
  ok = session.chat.delete_conversation(id_conv)
  if not ok:
    raise HTTPException(status_code=404, detail="Conversación no encontrada")
  return {"ok": True}


@router.get("/chat/conversations/{id_conv}/messages")
@rate_limit("60/minute")
def chat_messages(
  request: Request,
  id_conv: int,
  session: AppSession = Depends(require_session),
):
  require_sucursal(session)
  if not session.chat.switch_conversation(id_conv):
    raise HTTPException(status_code=404, detail="Conversación no encontrada")
  return {"messages": public_chat_messages(session.chat.get_ui_messages())}


@router.post("/chat")
@rate_limit("30/minute")
def chat_send(request: Request, body: ChatMessageBody, session: AppSession = Depends(require_session)):
  apply_chat_scope(session, id_sucursal=body.id_sucursal, id_isla=body.id_isla)
  require_sucursal(session)
  if is_workshop_staff(session.user.get("rol_nombre")):
    require_isla(session)
  if not session.chat.ensure_conversation():
    raise HTTPException(status_code=400, detail="Crea o selecciona una conversación primero.")
  result = session.chat.ask(body.message.strip())
  return public_chat_result(result)


@router.post("/chat/stream")
@rate_limit("30/minute")
def chat_stream(request: Request, body: ChatMessageBody, session: AppSession = Depends(require_session)):
  apply_chat_scope(session, id_sucursal=body.id_sucursal, id_isla=body.id_isla)
  require_sucursal(session)
  if is_workshop_staff(session.user.get("rol_nombre")):
    require_isla(session)
  if not session.chat.ensure_conversation():
    raise HTTPException(status_code=400, detail="Crea o selecciona una conversación primero.")
  message = body.message.strip()
  event_q: queue.Queue[tuple[str, Any]] = queue.Queue()

  def worker() -> None:
    try:
      result = session.chat.ask_stream(
        message,
        on_status=lambda phase, label: event_q.put(("status", {"phase": phase, "label": label})),
        on_token=lambda text: event_q.put(("token", {"text": text})),
      )
      event_q.put(("done", public_chat_result({
        "answer": result.get("answer"),
        "route": result.get("route"),
        "tool_calls": result.get("tool_calls", []),
        "metrics": result.get("metrics", {}),
      })))
    except Exception as exc:
      event_q.put(("error", {"message": str(exc)}))

  threading.Thread(target=worker, daemon=True).start()

  def iter_ndjson():
    while True:
      kind, payload = event_q.get()
      line = json.dumps({"type": kind, **payload}, ensure_ascii=False)
      yield line + "\n"
      if kind in ("done", "error"):
        break

  return StreamingResponse(iter_ndjson(), media_type="application/x-ndjson")


