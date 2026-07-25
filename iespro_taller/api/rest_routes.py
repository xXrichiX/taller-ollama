"""Endpoints REST — reemplazo de la UI Tkinter."""

from __future__ import annotations

import json
import queue
import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.session import (
  AppSession,
  create_session,
  delete_session,
  require_session,
  require_sucursal,
  user_payload,
)
from services import catalog_service, cita_service
from services.estado_labels import ESTADOS_MECANICO_UI, ESTADOS_UI, estado_a_etiqueta, etiqueta_a_estado
from services.password_policy import normalize_password, validate_password
from services.user_roles import (
  can_manage_branch,
  is_admin,
  is_cliente,
  is_mecanico,
  is_pending,
  is_workshop_staff,
  role_display_label,
)

router = APIRouter(prefix="/api")


# --- Auth ---


class LoginBody(BaseModel):
  email: str
  password: str


class RegisterBody(BaseModel):
  nombre: str
  email: str
  password: str


class SucursalActivaBody(BaseModel):
  id_sucursal: int


@router.post("/auth/login")
def auth_login(body: LoginBody):
  user = catalog_service.login(body.email.strip(), body.password)
  if not user:
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")
  if is_pending(user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Cuenta pendiente de asignación por administrador")

  if is_admin(user.get("rol_nombre")):
    user["sucursales_ids"] = [s["id"] for s in catalog_service.list_sucursales()]

  sucursales = user.get("sucursales_ids") or []
  if not sucursales and not is_cliente(user.get("rol_nombre")):
    raise HTTPException(status_code=400, detail="Usuario sin sucursal asignada")

  session = create_session(user)
  return {
    "token": session.token,
    "user": user_payload(user, session),
    "role_label": role_display_label(user.get("rol_nombre")),
  }


@router.post("/auth/register")
def auth_register(body: RegisterBody):
  result = catalog_service.register_usuario(
    body.nombre.strip(),
    body.email.strip().lower(),
    normalize_password(body.password),
  )
  if not result.get("ok"):
    raise HTTPException(status_code=400, detail=result.get("error", "No se pudo registrar"))

  user = catalog_service.login(body.email.strip().lower(), normalize_password(body.password))
  if not user:
    return {"ok": True, "message": "Cuenta creada. Inicia sesión.", "sucursal": result.get("sucursal")}

  session = create_session(user)
  return {
    "ok": True,
    "token": session.token,
    "user": user_payload(user, session),
    "sucursal": result.get("sucursal"),
  }


@router.post("/auth/logout")
def auth_logout(session: AppSession = Depends(require_session)):
  delete_session(session.token)
  return {"ok": True}


@router.get("/auth/me")
def auth_me(session: AppSession = Depends(require_session)):
  return {
    "user": user_payload(session.user, session),
    "role_label": role_display_label(session.user.get("rol_nombre")),
    "permissions": _permissions(session),
  }


@router.put("/session/sucursal")
def set_sucursal(body: SucursalActivaBody, session: AppSession = Depends(require_session)):
  allowed = session.user.get("sucursales_ids") or []
  if is_admin(session.user.get("rol_nombre")):
    allowed = [s["id"] for s in catalog_service.list_sucursales()]
  if body.id_sucursal not in allowed:
    raise HTTPException(status_code=403, detail="Sucursal no permitida")
  session.id_sucursal = body.id_sucursal
  session.chat.id_sucursal = body.id_sucursal
  return {"ok": True, "id_sucursal": body.id_sucursal}


def _permissions(session: AppSession) -> dict[str, bool]:
  rol = session.user.get("rol_nombre")
  return {
    "is_admin": is_admin(rol),
    "is_mecanico": is_mecanico(rol),
    "is_cliente": is_cliente(rol),
    "is_staff": is_workshop_staff(rol),
    "can_manage_branch": can_manage_branch(rol),
    "can_manage_citas": is_workshop_staff(rol),
    "can_create_citas": can_manage_branch(rol) or is_mecanico(rol) or is_cliente(rol),
    "can_manage_usuarios": is_admin(rol),
  }


def _requires_sucursal(session: AppSession) -> bool:
  rol = session.user.get("rol_nombre")
  return bool((is_admin(rol) or is_mecanico(rol)) and not session.id_sucursal)


# --- Dashboard ---


@router.get("/dashboard")
def dashboard(session: AppSession = Depends(require_session)):
  if _requires_sucursal(session):
    return {"stats": {}, "recent_citas": []}

  rol = session.user.get("rol_nombre")
  stats: dict[str, int] = {}
  citas_filters = _citas_filters(session)

  citas = cita_service.list_citas(**citas_filters)
  pendientes = sum(1 for c in citas if c.get("estado") in ("PENDIENTE", "RECIBIDO"))
  en_proceso = sum(1 for c in citas if c.get("estado") in ("EN_PROCESO", "EN_REPARACION", "DIAGNOSTICO"))
  completadas = sum(1 for c in citas if c.get("estado") in ("COMPLETADA", "FINALIZADO"))

  if is_cliente(rol):
    vehiculos = cita_service.list_vehiculos(id_cliente=session.id_cliente)
    stats = {
      "vehiculos": len(vehiculos),
      "citas": len(citas),
      "pendientes": pendientes,
      "en_proceso": en_proceso,
      "completadas": completadas,
    }
  elif is_mecanico(rol):
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

  recent = []
  for c in citas[:12]:
    recent.append({
      "id": c["id"],
      "cliente": c.get("cliente"),
      "placa": c.get("placa"),
      "estado": estado_a_etiqueta(c.get("estado")),
      "mecanico": c.get("mecanico"),
      "isla": c.get("isla"),
      "descripcion_fallo": (c.get("descripcion_fallo") or "")[:70],
    })

  title = "Panel del taller"
  if is_cliente(rol):
    title = "Mi panel"
  elif is_mecanico(rol):
    title = "Panel del mecánico"

  return {"title": title, "stats": stats, "recent_citas": recent}


def _citas_filters(session: AppSession) -> dict[str, Any]:
  filters: dict[str, Any] = {}
  if is_cliente(session.user.get("rol_nombre")) and session.id_cliente:
    filters["id_cliente"] = session.id_cliente
  if session.id_sucursal:
    filters["id_sucursal"] = session.id_sucursal
  if is_mecanico(session.user.get("rol_nombre")):
    filters["id_mecanico"] = session.user["id"]
  return filters


def _clientes_filters(session: AppSession) -> dict[str, Any]:
  if is_mecanico(session.user.get("rol_nombre")):
    return {"id_mecanico": session.user["id"]}
  if session.id_sucursal:
    return {"id_sucursal": session.id_sucursal}
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
  if is_admin(session.user.get("rol_nombre")):
    rows = catalog_service.list_sucursales()
  else:
    rows = catalog_service.list_sucursales_usuario(session.user["id"])
  for r in rows:
    r["activo_label"] = "Sí" if r.get("activo", 1) else "No"
  return {"sucursales": rows}


@router.post("/sucursales")
def create_sucursal(body: SucursalCreate, session: AppSession = Depends(require_session)):
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")
  nombre = body.nombre.strip()
  if not nombre:
    raise HTTPException(status_code=400, detail="Nombre requerido")
  id_sucursal = catalog_service.create_sucursal(nombre, body.direccion.strip())
  return {"ok": True, "id": id_sucursal}


@router.get("/sucursales/{id_sucursal}/islas")
def list_islas(id_sucursal: int, session: AppSession = Depends(require_session)):
  rows = cita_service.list_islas(id_sucursal)
  for r in rows:
    r["activo_label"] = "Sí" if r.get("activo", 1) else "No"
  return {"islas": rows}


@router.post("/sucursales/{id_sucursal}/islas")
def create_isla(
  id_sucursal: int,
  body: IslaCreate,
  session: AppSession = Depends(require_session),
):
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")
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
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")
  return {"items": catalog_service.list_puestos()}


@router.get("/catalogos/mantenimiento")
def catalog_mantenimiento(session: AppSession = Depends(require_session)):
  id_sucursal = require_sucursal(session)
  return {"items": catalog_service.list_tipos_mantenimiento(id_sucursal)}


@router.get("/catalogos/estados-cita")
def catalog_estados(session: AppSession = Depends(require_session)):
  if is_mecanico(session.user.get("rol_nombre")):
    return {"items": ESTADOS_MECANICO_UI}
  return {"items": ESTADOS_UI}


@router.get("/catalogos/mecanicos")
def catalog_mecanicos(session: AppSession = Depends(require_session)):
  id_sucursal = require_sucursal(session)
  return {"items": cita_service.list_mecanicos(id_sucursal)}


# --- Clientes ---


class ClienteCreate(BaseModel):
  nombre: str
  telefono: str = ""
  email: str = ""


@router.get("/clientes")
def list_clientes(session: AppSession = Depends(require_session)):
  if _requires_sucursal(session):
    return {"clientes": []}
  rows = catalog_service.list_clientes(**_clientes_filters(session))
  return {"clientes": rows}


@router.post("/clientes")
def create_cliente(body: ClienteCreate, session: AppSession = Depends(require_session)):
  if not is_workshop_staff(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Sin permiso")
  id_cliente = catalog_service.create_cliente(
    body.nombre.strip(),
    body.telefono.strip(),
    body.email.strip(),
    None,
  )
  return {"ok": True, "id": id_cliente}


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
def list_vehiculos(
  id_cliente: int | None = None,
  session: AppSession = Depends(require_session),
):
  if _requires_sucursal(session) and not is_cliente(session.user.get("rol_nombre")):
    return {"vehiculos": []}

  rol = session.user.get("rol_nombre")
  if id_cliente and is_workshop_staff(rol):
    rows = cita_service.list_vehiculos(id_cliente=id_cliente)
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
def get_cita(id_cita: int, session: AppSession = Depends(require_session)):
  cita = cita_service.get_cita_by_id(id_cita)
  if not cita:
    raise HTTPException(status_code=404, detail="Cita no encontrada")
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
  elif is_mecanico(rol):
    defaults = cita_service.get_default_asignacion_taller(id_sucursal)
    id_cliente = body.id_cliente
    if not id_cliente:
      raise HTTPException(status_code=400, detail="Cliente requerido")
    id_mecanico = session.user["id"]
    id_isla = defaults["id_isla"]
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

  if is_mecanico(session.user.get("rol_nombre")):
    if cita.get("id_mecanico") != session.user["id"]:
      raise HTTPException(status_code=403, detail="Solo citas asignadas a ti")

  estado_raw = etiqueta_a_estado(body.estado) if body.estado else None
  if body.estado and not estado_raw:
    raise HTTPException(status_code=400, detail="Estado inválido")

  if estado_raw == "CANCELADA":
    if is_mecanico(session.user.get("rol_nombre")):
      raise HTTPException(status_code=403, detail="Solo admin puede cancelar")
    result = cita_service.cambiar_estado_cita(id_cita, estado_raw)
  elif is_mecanico(session.user.get("rol_nombre")):
    if not estado_raw:
      raise HTTPException(status_code=400, detail="Estado requerido")
    result = cita_service.cambiar_estado_cita(id_cita, estado_raw)
  else:
    updates: dict[str, Any] = {}
    if estado_raw and estado_raw != "CANCELADA":
      updates["estado"] = estado_raw
    if can_manage_branch(session.user.get("rol_nombre")):
      if body.id_mecanico is not None:
        updates["id_mecanico"] = body.id_mecanico
      if body.id_isla is not None:
        updates["id_isla"] = body.id_isla
    result = cita_service.update_cita(id_cita, updates) if updates else {"ok": True}

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
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")
  if _requires_sucursal(session):
    return {"usuarios": []}
  rows = catalog_service.list_usuarios(session.id_sucursal)
  for r in rows:
    r["puesto"] = r.get("puesto") or "—"
  return {"usuarios": rows}


@router.get("/usuarios/{id_usuario}/sucursales")
def usuario_sucursales(id_usuario: int, session: AppSession = Depends(require_session)):
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")
  return {"sucursales": catalog_service.list_sucursales_usuario(id_usuario)}


@router.post("/usuarios")
def create_usuario(body: UsuarioCreate, session: AppSession = Depends(require_session)):
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")

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
  if not is_admin(session.user.get("rol_nombre")):
    raise HTTPException(status_code=403, detail="Solo administrador")

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


class TokenBody(BaseModel):
  token: str


@router.post("/rag/bootstrap")
def rag_bootstrap(session: AppSession = Depends(require_session)):
  ok, msg = session.chat.bootstrap()
  return {"ok": ok, "message": msg}


@router.get("/chat/conversations")
def chat_conversations(session: AppSession = Depends(require_session)):
  require_sucursal(session)
  return {"conversations": session.chat.list_conversations()}


@router.post("/chat/conversations")
def chat_new_conversation(session: AppSession = Depends(require_session)):
  require_sucursal(session)
  session.chat.start_new_conversation()
  session.chat.ensure_conversation()
  return {"ok": True}


@router.post("/chat/conversations/{id_conv}/activate")
def chat_activate(id_conv: int, session: AppSession = Depends(require_session)):
  require_sucursal(session)
  ok = session.chat.switch_conversation(id_conv)
  if not ok:
    raise HTTPException(status_code=404, detail="Conversación no encontrada")
  return {"ok": True}


@router.get("/chat/conversations/{id_conv}/messages")
def chat_messages(id_conv: int, session: AppSession = Depends(require_session)):
  require_sucursal(session)
  session.chat.switch_conversation(id_conv)
  return {"messages": session.chat.get_ui_messages()}


@router.post("/chat")
def chat_send(body: ChatMessageBody, session: AppSession = Depends(require_session)):
  if body.id_sucursal:
    session.id_sucursal = body.id_sucursal
    session.chat.id_sucursal = body.id_sucursal
  require_sucursal(session)
  session.chat.ensure_conversation()
  result = session.chat.ask(body.message.strip())
  return {
    "answer": result.get("answer"),
    "route": result.get("route"),
    "tool_calls": result.get("tool_calls", []),
    "metrics": result.get("metrics", {}),
  }


@router.post("/chat/stream")
def chat_stream(body: ChatMessageBody, session: AppSession = Depends(require_session)):
  if body.id_sucursal:
    session.id_sucursal = body.id_sucursal
    session.chat.id_sucursal = body.id_sucursal
  require_sucursal(session)
  session.chat.ensure_conversation()
  message = body.message.strip()
  event_q: queue.Queue[tuple[str, Any]] = queue.Queue()

  def worker() -> None:
    try:
      result = session.chat.ask_stream(
        message,
        on_status=lambda phase, label: event_q.put(("status", {"phase": phase, "label": label})),
        on_token=lambda text: event_q.put(("token", {"text": text})),
      )
      event_q.put(("done", {
        "answer": result.get("answer"),
        "route": result.get("route"),
        "tool_calls": result.get("tool_calls", []),
        "metrics": result.get("metrics", {}),
      }))
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


