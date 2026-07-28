import json
from typing import Any, Callable

from services import cita_service, catalog_service, inventory_service


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "contar_citas",
            "description": "Cuenta citas del taller, opcionalmente filtradas por estado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "estado": {"type": "string", "enum": ["PENDIENTE", "EN_PROCESO", "COMPLETADA", "CANCELADA"]},
                    "id_sucursal": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_citas",
            "description": "Lista citas con cliente, vehículo, falla, mecánico e isla.",
            "parameters": {
                "type": "object",
                "properties": {"id_sucursal": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mecanicos_en_isla",
            "description": "Obtiene los mecánicos asignados a una isla específica.",
            "parameters": {
                "type": "object",
                "properties": {"id_isla": {"type": "integer"}},
                "required": ["id_isla"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_islas",
            "description": "Lista islas/bahías del taller de una sucursal.",
            "parameters": {
                "type": "object",
                "properties": {"id_sucursal": {"type": "integer"}},
                "required": ["id_sucursal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vehiculos_de_cliente",
            "description": "Lista vehículos registrados de un cliente por id de cliente.",
            "parameters": {
                "type": "object",
                "properties": {"id_cliente": {"type": "integer"}},
                "required": ["id_cliente"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_clientes",
            "description": "Lista todos los clientes del taller con id y nombre.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_vehiculos",
            "description": "Lista vehículos. Opcionalmente filtra por id_cliente.",
            "parameters": {
                "type": "object",
                "properties": {"id_cliente": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_mecanicos",
            "description": "Lista mecánicos disponibles de la sucursal.",
            "parameters": {
                "type": "object",
                "properties": {"id_sucursal": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_cliente_natural",
            "description": (
                "Registra un cliente nuevo en el taller. Solo llámala cuando tengas al menos el nombre. "
                "Si faltan datos, pregunta al usuario antes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre completo del cliente"},
                    "telefono": {"type": "string", "description": "Teléfono (solo números)"},
                    "email": {"type": "string", "description": "Correo electrónico"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_vehiculo_natural",
            "description": (
                "Registra un vehículo para un cliente (por nombre de cliente o placa). "
                "Requiere placa; modelo y marca son opcionales."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "placa": {"type": "string"},
                    "nombre_cliente": {"type": "string", "description": "Cliente dueño del vehículo"},
                    "modelo": {"type": "string"},
                    "marca": {"type": "string", "description": "Marca del auto, ej. Toyota"},
                    "id_sucursal": {"type": "integer"},
                },
                "required": ["placa"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_servicio_natural",
            "description": (
                "Crea un servicio del catálogo del taller (tipo de mantenimiento). "
                "Requiere nombre; precio y descripción son opcionales."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "descripcion": {"type": "string"},
                    "precio": {"type": "number", "description": "Precio en pesos"},
                    "id_sucursal": {"type": "integer"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_inventario_natural",
            "description": (
                "Agrega un artículo al inventario de la isla activa. "
                "Requiere nombre; cantidad, código y precio son opcionales."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "codigo": {"type": "string"},
                    "cantidad": {"type": "number"},
                    "stock_minimo": {"type": "number"},
                    "precio_unitario": {"type": "number"},
                    "unidad": {"type": "string", "description": "Ej. pza, lt, kg"},
                    "descripcion": {"type": "string"},
                    "id_isla": {"type": "integer"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "contar_inventario",
            "description": (
                "Cuenta artículos en inventario/stock de la isla activa. "
                "Opcionalmente solo los que tienen stock bajo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id_isla": {"type": "integer", "description": "Isla/bahía (se usa la activa si no se indica)"},
                    "solo_stock_bajo": {
                        "type": "boolean",
                        "description": "Si es true, solo cuenta artículos con stock en o bajo el mínimo",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_inventario",
            "description": (
                "Lista inventario/stock de piezas y refacciones de la isla activa. "
                "Usa busqueda para filtrar por nombre o código; solo_stock_bajo para alertas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id_isla": {"type": "integer", "description": "Isla/bahía (se usa la activa si no se indica)"},
                    "busqueda": {"type": "string", "description": "Filtrar por nombre, código o descripción"},
                    "solo_stock_bajo": {
                        "type": "boolean",
                        "description": "Si es true, solo artículos con cantidad en o bajo el mínimo",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_cita_natural",
            "description": (
                "Crea una cita usando nombres y placa (NO pidas IDs al usuario). "
                "Solo llámala cuando tengas cliente, placa o vehículo, y descripción de la falla. "
                "Si faltan datos, pregunta al usuario antes de llamar esta función. "
                "Mecánico e isla son opcionales si el taller asigna automáticamente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_cliente": {"type": "string", "description": "Nombre del cliente, ej. Roberto García"},
                    "placa": {"type": "string", "description": "Placa del vehículo, ej. ABC-123"},
                    "modelo_vehiculo": {"type": "string", "description": "Alternativa si no hay placa"},
                    "nombre_mecanico": {"type": "string", "description": "Nombre del mecánico, ej. Carlos"},
                    "isla": {"type": "string", "description": "Isla por nombre o número, ej. '1' o 'Isla Diagnóstico'"},
                    "descripcion_fallo": {"type": "string"},
                    "id_sucursal": {"type": "integer"},
                    "fecha_cita": {"type": "string", "description": "YYYY-MM-DD HH:MM:SS"},
                    "servicios": {"type": "array", "items": {"type": "integer"}},
                    "asignacion_automatica": {
                        "type": "boolean",
                        "description": "True si el taller asigna mecánico e isla sin pedirlos al usuario",
                    },
                },
                "required": [
                    "nombre_cliente",
                    "descripcion_fallo",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_cliente",
            "description": "Busca un cliente por nombre parcial.",
            "parameters": {
                "type": "object",
                "properties": {"nombre": {"type": "string"}},
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_vehiculo",
            "description": "Busca un vehículo por placa o modelo. Opcionalmente filtra por id_cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "placa": {"type": "string"},
                    "modelo": {"type": "string"},
                    "id_cliente": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cambiar_estado_cita_natural",
            "description": "Cambia el estado de una cita usando placa o id_cita (no pidas IDs internos al usuario).",
            "parameters": {
                "type": "object",
                "properties": {
                    "placa": {"type": "string"},
                    "id_cita": {"type": "integer"},
                    "estado": {
                        "type": "string",
                        "enum": ["PENDIENTE", "EN_PROCESO", "COMPLETADA", "CANCELADA"],
                    },
                    "id_sucursal": {"type": "integer"},
                },
                "required": ["estado"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_fallas_similares",
            "description": "Busca fallas históricas similares usando RAG semántico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "descripcion": {"type": "string"},
                    "limite": {"type": "integer"},
                },
                "required": ["descripcion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_cita_natural",
            "description": (
                "Cancela una cita (estado CANCELADA, inactiva). "
                "Usar cuando el usuario diga cancelar, eliminar, borrar o quitar una cita. "
                "NO borra el registro de la base de datos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "placa": {"type": "string"},
                    "id_cita": {"type": "integer"},
                    "id_sucursal": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "editar_cita_natural",
            "description": (
                "Edita una cita activa (PENDIENTE o EN_PROCESO) usando placa o id_cita. "
                "Puede cambiar falla, mecánico, isla, fecha u observaciones."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "placa": {"type": "string"},
                    "id_cita": {"type": "integer"},
                    "descripcion_fallo": {"type": "string"},
                    "nombre_mecanico": {"type": "string"},
                    "isla": {"type": "string"},
                    "fecha_cita": {"type": "string", "description": "YYYY-MM-DD HH:MM:SS"},
                    "fecha_compromiso": {"type": "string", "description": "YYYY-MM-DD"},
                    "hora_compromiso": {"type": "string", "description": "HH:MM:SS"},
                    "id_sucursal": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cambiar_estado_cita",
            "description": "Cambia el estado de una cita existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_cita": {"type": "integer"},
                    "estado": {"type": "string", "enum": ["PENDIENTE", "EN_PROCESO", "COMPLETADA", "CANCELADA"]},
                },
                "required": ["id_cita", "estado"],
            },
        },
    },
]


CLIENTE_DENIED_TOOLS = frozenset({
    "listar_clientes",
    "buscar_cliente",
    "listar_mecanicos",
    "listar_islas",
    "listar_inventario",
    "contar_inventario",
    "mecanicos_en_isla",
    "cambiar_estado_cita_natural",
    "cambiar_estado_cita",
    "editar_cita_natural",
    "crear_cliente_natural",
    "crear_servicio_natural",
    "crear_inventario_natural",
})


MECANICO_DENIED_TOOLS = frozenset({
    "listar_clientes",
    "buscar_cliente",
    "listar_mecanicos",
    "listar_islas",
    "mecanicos_en_isla",
    "crear_cita_natural",
    "editar_cita_natural",
    "cancelar_cita_natural",
    "crear_cliente_natural",
    "crear_vehiculo_natural",
    "crear_servicio_natural",
    "crear_inventario_natural",
})


class ToolsService:
    def __init__(
        self,
        rag_service=None,
        *,
        id_cliente: int | None = None,
        nombre_cliente: str | None = None,
        es_cliente: bool = False,
        id_mecanico: int | None = None,
        es_mecanico: bool = False,
        es_propietario: bool = False,
        id_sucursal: int | None = None,
        id_isla: int | None = None,
    ):
        self.rag = rag_service
        self.id_cliente = id_cliente
        self.nombre_cliente = nombre_cliente
        self.es_cliente = es_cliente
        self.id_mecanico = id_mecanico
        self.es_mecanico = es_mecanico
        self.es_propietario = es_propietario
        self.id_sucursal = id_sucursal
        self.id_isla = id_isla
        self._handlers: dict[str, Callable[[dict], Any]] = {
            "contar_citas": self._contar_citas,
            "listar_citas": self._listar_citas,
            "listar_clientes": self._listar_clientes,
            "listar_vehiculos": self._listar_vehiculos,
            "listar_mecanicos": self._listar_mecanicos,
            "crear_cita_natural": self._crear_cita_natural,
            "buscar_cliente": self._buscar_cliente,
            "buscar_vehiculo": self._buscar_vehiculo,
            "crear_cliente_natural": self._crear_cliente_natural,
            "crear_vehiculo_natural": self._crear_vehiculo_natural,
            "crear_servicio_natural": self._crear_servicio_natural,
            "crear_inventario_natural": self._crear_inventario_natural,
            "cambiar_estado_cita_natural": self._cambiar_estado_cita_natural,
            "cancelar_cita_natural": self._cancelar_cita_natural,
            "editar_cita_natural": self._editar_cita_natural,
            "mecanicos_en_isla": self._mecanicos_en_isla,
            "listar_islas": self._listar_islas,
            "listar_inventario": self._listar_inventario,
            "contar_inventario": self._contar_inventario,
            "vehiculos_de_cliente": self._vehiculos_de_cliente,
            "buscar_fallas_similares": self._buscar_fallas_similares,
            "cambiar_estado_cita": self._cambiar_estado_cita,
        }

    def execute(self, name: str, arguments: dict) -> Any:
        if name not in self._handlers:
            return {
                "ok": False,
                "error": f"Tool desconocida: {name}",
                "recoverable": False,
            }
        if self.es_cliente and name in CLIENTE_DENIED_TOOLS:
            return {
                "ok": False,
                "error": "Esa acción solo la puede hacer el personal del taller.",
                "recoverable": True,
            }
        if self.es_mecanico and not self.es_propietario and name in MECANICO_DENIED_TOOLS:
            return {
                "ok": False,
                "error": "Como mecánico solo puedes consultar y actualizar estado de tus citas asignadas.",
                "recoverable": True,
            }
        if self.es_propietario and name in {"listar_mecanicos", "listar_islas", "mecanicos_en_isla"}:
            return {
                "ok": False,
                "error": "Eres el único mecánico de tu taller; no hace falta listar islas u otros mecánicos.",
                "recoverable": True,
            }
        try:
            scoped_args = self._scope_arguments(name, arguments or {})
            result = self._handlers[name](scoped_args)
            if isinstance(result, dict) and result.get("error") and result.get("ok") is not False:
                return {
                    "ok": False,
                    "error": str(result["error"]),
                    "recoverable": True,
                }
            return result
        except Exception as exc:
            from services.tool_resilience import sanitize_tool_result

            return sanitize_tool_result(name, None, exc=exc)

    def _scope_arguments(self, name: str, args: dict) -> dict:
        scoped = dict(args)
        if self.es_cliente and self.id_cliente:
            if name in ("listar_citas", "contar_citas", "listar_vehiculos", "vehiculos_de_cliente", "buscar_vehiculo"):
                scoped["id_cliente"] = self.id_cliente
            if name == "crear_vehiculo_natural":
                scoped["nombre_cliente"] = self.nombre_cliente
            if name == "crear_cita_natural" and self.nombre_cliente:
                scoped["nombre_cliente"] = self.nombre_cliente
                scoped.setdefault("asignacion_automatica", True)
            if name in ("cancelar_cita_natural",) and scoped.get("placa"):
                scoped["id_cliente"] = self.id_cliente
            return scoped
        if self.es_propietario and self.id_sucursal:
            scoped["id_sucursal"] = self.id_sucursal
            if name == "crear_cita_natural":
                scoped["asignacion_automatica"] = True
            if self.id_isla and name in (
                "listar_citas",
                "contar_citas",
                "crear_cita_natural",
                "crear_vehiculo_natural",
                "crear_servicio_natural",
                "crear_inventario_natural",
                "cambiar_estado_cita_natural",
                "cancelar_cita_natural",
                "editar_cita_natural",
                "listar_inventario",
                "contar_inventario",
            ):
                scoped["id_isla"] = self.id_isla
            scoped.pop("id_mecanico", None)
            scoped.pop("id_mecanico_asignado", None)
            return scoped
        if self.es_mecanico and self.id_mecanico:
            if self.id_sucursal:
                scoped["id_sucursal"] = self.id_sucursal
            if self.id_isla and name in (
                "listar_citas",
                "contar_citas",
                "cambiar_estado_cita_natural",
                "cancelar_cita_natural",
                "buscar_fallas_similares",
                "crear_cita_natural",
                "editar_cita_natural",
                "listar_inventario",
                "contar_inventario",
            ):
                scoped["id_isla"] = self.id_isla
                scoped.pop("id_mecanico", None)
            elif name in (
                "listar_citas",
                "contar_citas",
                "cambiar_estado_cita_natural",
                "cancelar_cita_natural",
                "buscar_fallas_similares",
            ):
                scoped["id_mecanico"] = self.id_mecanico
            if name == "listar_vehiculos":
                scoped["id_mecanico_asignado"] = self.id_mecanico
                scoped.pop("id_cliente", None)
            if name == "buscar_vehiculo":
                scoped["id_mecanico_asignado"] = self.id_mecanico
                if self.id_sucursal:
                    scoped["id_sucursal"] = self.id_sucursal
        if self.id_isla and name in ("listar_inventario", "contar_inventario", "crear_inventario_natural"):
            scoped.setdefault("id_isla", self.id_isla)
        if self.id_sucursal and name in ("crear_cliente_natural", "crear_vehiculo_natural", "crear_servicio_natural"):
            scoped.setdefault("id_sucursal", self.id_sucursal)
        return scoped

    def _missing_cita_fields(self, args: dict, auto: bool) -> list[str]:
        missing: list[str] = []
        if not (args.get("nombre_cliente") or "").strip():
            missing.append("nombre del cliente")
        if not (args.get("descripcion_fallo") or "").strip():
            missing.append("descripción de la falla")
        if not args.get("placa") and not args.get("modelo_vehiculo"):
            missing.append("placa o modelo del vehículo")
        if not auto:
            if not (args.get("nombre_mecanico") or "").strip():
                missing.append("nombre del mecánico")
            if not (args.get("isla") or "").strip() and not args.get("id_isla"):
                missing.append("isla o bahía")
        return missing

    def _assert_cita_del_cliente(self, id_cita: int) -> dict | None:
        if not self.es_cliente or not self.id_cliente:
            return None
        cita = cita_service.get_cita_by_id(id_cita)
        if not cita:
            return {"ok": False, "error": "Cita no encontrada."}
        if cita.get("id_cliente") != self.id_cliente:
            return {"ok": False, "error": "Solo puedes gestionar tus propias citas."}
        return None

    def _assert_cita_del_mecanico(self, id_cita: int) -> dict | None:
        if self.es_propietario or not self.es_mecanico or not self.id_mecanico:
            return None
        cita = cita_service.get_cita_by_id(id_cita)
        if not cita:
            return {"ok": False, "error": "Cita no encontrada."}
        if cita.get("id_mecanico") != self.id_mecanico:
            return {"ok": False, "error": "Solo puedes gestionar citas asignadas a ti."}
        if self.id_sucursal and cita.get("id_sucursal") and cita["id_sucursal"] != self.id_sucursal:
            return {"ok": False, "error": "Esa cita no pertenece a la sucursal activa."}
        return None

    def _contar_citas(self, args: dict) -> dict:
        total = cita_service.count_citas(
            args.get("estado"),
            args.get("id_sucursal"),
            args.get("id_cliente"),
            args.get("id_mecanico"),
            args.get("id_isla"),
        )
        return {"total": total, "estado": args.get("estado"), "id_sucursal": args.get("id_sucursal")}

    def _listar_citas(self, args: dict) -> list[dict]:
        citas = cita_service.list_citas(
            args.get("id_sucursal"),
            args.get("id_cliente"),
            args.get("id_mecanico"),
            args.get("id_isla"),
        )
        return citas[:15]

    def _mecanicos_en_isla(self, args: dict) -> list[dict]:
        return cita_service.get_mecanicos_por_isla(args["id_isla"])

    def _listar_islas(self, args: dict) -> list[dict]:
        return cita_service.list_islas(args["id_sucursal"])

    def _listar_inventario(self, args: dict) -> list[dict] | dict[str, Any]:
        id_isla = args.get("id_isla") or self.id_isla
        if not id_isla:
            return {
                "ok": False,
                "error": "Selecciona una isla en la barra superior para consultar inventario.",
            }
        rows = inventory_service.list_inventario(int(id_isla))
        busqueda = (args.get("busqueda") or "").strip().lower()
        if busqueda:
            rows = [
                row for row in rows
                if busqueda in (row.get("nombre") or "").lower()
                or busqueda in (row.get("codigo") or "").lower()
                or busqueda in (row.get("descripcion") or "").lower()
            ]
        if args.get("solo_stock_bajo"):
            rows = [row for row in rows if row.get("stock_bajo")]
        return rows[:40]

    def _contar_inventario(self, args: dict) -> dict[str, Any]:
        id_isla = args.get("id_isla") or self.id_isla
        if not id_isla:
            return {
                "ok": False,
                "error": "Selecciona una isla en la barra superior para consultar inventario.",
            }
        rows = inventory_service.list_inventario(int(id_isla))
        if args.get("solo_stock_bajo"):
            rows = [row for row in rows if row.get("stock_bajo")]
        return {
            "ok": True,
            "total": len(rows),
            "solo_stock_bajo": bool(args.get("solo_stock_bajo")),
            "id_isla": int(id_isla),
        }

    def _vehiculos_de_cliente(self, args: dict) -> list[dict]:
        return cita_service.list_vehiculos(args["id_cliente"])

    def _listar_clientes(self, args: dict) -> list[dict]:
        return catalog_service.list_clientes(id_sucursal=self.id_sucursal)

    def _listar_vehiculos(self, args: dict) -> list[dict]:
        return cita_service.list_vehiculos(
            id_cliente=args.get("id_cliente"),
            id_sucursal=args.get("id_sucursal"),
            id_mecanico_asignado=args.get("id_mecanico_asignado"),
        )

    def _listar_mecanicos(self, args: dict) -> list[dict]:
        return cita_service.list_mecanicos(args.get("id_sucursal", 1))

    def _resolve_marca_id(self, nombre: str | None) -> int:
        marcas = catalog_service.list_marcas()
        if not marcas:
            return 1
        if nombre:
            norm = nombre.strip().lower()
            for m in marcas:
                if (m.get("nombre") or "").lower() == norm:
                    return int(m["id"])
            for m in marcas:
                if norm in (m.get("nombre") or "").lower():
                    return int(m["id"])
        return int(marcas[0]["id"])

    def _crear_cliente_natural(self, args: dict) -> dict:
        nombre = (args.get("nombre") or "").strip()
        if len(nombre) < 2:
            return {
                "ok": False,
                "error": "Para crear el cliente necesito el nombre completo.",
                "faltan": ["nombre"],
                "recoverable": True,
            }
        telefono = (args.get("telefono") or "").strip()
        email = (args.get("email") or "").strip()
        if telefono and (len(telefono) < 7 or not any(ch.isdigit() for ch in telefono)):
            return {"ok": False, "error": "Teléfono inválido. Usa solo números.", "recoverable": True}
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            return {"ok": False, "error": "Correo inválido.", "recoverable": True}
        id_cliente = catalog_service.create_cliente(
            nombre, telefono, email, None, self.id_sucursal
        )
        return {"ok": True, "id_cliente": id_cliente, "nombre": nombre, "telefono": telefono or None}

    def _crear_vehiculo_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        placa_raw = (args.get("placa") or "").strip()
        if not placa_raw:
            return {
                "ok": False,
                "error": "Para registrar el vehículo necesito la placa.",
                "faltan": ["placa"],
                "recoverable": True,
            }
        placa = cita_service._norm_placa(placa_raw)
        if not placa:
            placa = placa_raw.upper()

        id_sucursal = args.get("id_sucursal") or self.id_sucursal or DEFAULT_SUCURSAL_ID
        id_cliente = self.id_cliente if self.es_cliente else None
        nombre_cliente = (args.get("nombre_cliente") or "").strip()

        if self.es_cliente and self.id_cliente:
            id_cliente = self.id_cliente
        elif nombre_cliente:
            cliente_res = cita_service.find_cliente_by_nombre(nombre_cliente)
            if not cliente_res.get("ok"):
                return cliente_res
            id_cliente = cliente_res["cliente"]["id"]
        else:
            return {
                "ok": False,
                "error": "Indica a qué cliente pertenece el vehículo (nombre del cliente).",
                "faltan": ["nombre del cliente"],
                "recoverable": True,
            }

        marcas = catalog_service.list_marcas()
        combustibles = catalog_service.list_tipos_combustible()
        unidades = catalog_service.list_tipos_unidad()
        id_marca = self._resolve_marca_id(args.get("marca"))
        id_combustible = int(combustibles[0]["id"]) if combustibles else 1
        id_unidad = int(unidades[0]["id"]) if unidades else 1
        modelo = (args.get("modelo") or "Sin especificar").strip() or "Sin especificar"

        id_usuario = catalog_service.ensure_cliente_usuario(int(id_cliente))
        id_mecanico = self.id_mecanico if self.es_mecanico and not self.es_propietario else None

        vid = cita_service.create_vehiculo({
            "numero_economico": "",
            "placa": placa,
            "serie": "",
            "id_marca": id_marca,
            "modelo": modelo,
            "id_tipo_combustible": id_combustible,
            "id_tipo_unidad": id_unidad,
            "kilometraje": 0,
            "dias_mantenimiento": 90,
            "observaciones": None,
            "id_cliente": id_cliente,
            "id_usuario": id_usuario,
            "id_sucursal": id_sucursal,
            "id_mecanico_asignado": id_mecanico,
        })
        marca_nombre = next((m["nombre"] for m in marcas if int(m["id"]) == id_marca), "")
        return {
            "ok": True,
            "id_vehiculo": vid,
            "placa": placa,
            "modelo": modelo,
            "marca": marca_nombre,
            "id_cliente": id_cliente,
        }

    def _crear_servicio_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        nombre = (args.get("nombre") or "").strip()
        if len(nombre) < 2:
            return {
                "ok": False,
                "error": "Para crear el servicio necesito el nombre.",
                "faltan": ["nombre del servicio"],
                "recoverable": True,
            }
        id_sucursal = args.get("id_sucursal") or self.id_sucursal or DEFAULT_SUCURSAL_ID
        descripcion = (args.get("descripcion") or "").strip()
        precio = float(args.get("precio") or 0)
        if precio < 0:
            return {"ok": False, "error": "El precio no puede ser negativo.", "recoverable": True}
        sid = catalog_service.create_tipo_mantenimiento(nombre, descripcion, precio, int(id_sucursal))
        return {"ok": True, "id_servicio": sid, "nombre": nombre, "precio": precio}

    def _crear_inventario_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        nombre = (args.get("nombre") or "").strip()
        if len(nombre) < 2:
            return {
                "ok": False,
                "error": "Para agregar al inventario necesito el nombre del artículo.",
                "faltan": ["nombre"],
                "recoverable": True,
            }
        id_isla = args.get("id_isla") or self.id_isla
        if not id_isla:
            return {
                "ok": False,
                "error": "Selecciona una isla en la barra superior para agregar inventario.",
                "recoverable": True,
            }
        id_sucursal = args.get("id_sucursal") or self.id_sucursal or DEFAULT_SUCURSAL_ID
        cantidad = float(args.get("cantidad") or 0)
        stock_minimo = float(args.get("stock_minimo") or 0)
        precio_unitario = float(args.get("precio_unitario") or 0)
        if cantidad < 0 or stock_minimo < 0 or precio_unitario < 0:
            return {"ok": False, "error": "Cantidades y precios no pueden ser negativos.", "recoverable": True}
        iid = inventory_service.create_item(int(id_sucursal), int(id_isla), {
            "codigo": (args.get("codigo") or "").strip(),
            "nombre": nombre,
            "descripcion": (args.get("descripcion") or "").strip(),
            "cantidad": cantidad,
            "stock_minimo": stock_minimo,
            "precio_unitario": precio_unitario,
            "unidad": (args.get("unidad") or "pza").strip() or "pza",
        })
        return {
            "ok": True,
            "id_inventario": iid,
            "nombre": nombre,
            "cantidad": cantidad,
            "id_isla": int(id_isla),
        }

    def _crear_cita_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        id_sucursal = args.get("id_sucursal", DEFAULT_SUCURSAL_ID)

        forced_isla = args.get("id_isla") or self.id_isla
        auto = bool(
            args.get("asignacion_automatica")
            or self.es_propietario
            or self.es_cliente
            or (forced_isla and self.es_mecanico)
        )
        missing = self._missing_cita_fields(args, auto)
        if missing:
            return {
                "ok": False,
                "error": "Para crear la cita faltan: " + ", ".join(missing) + ".",
                "faltan": missing,
                "recoverable": True,
            }

        cliente_res = cita_service.find_cliente_by_nombre(args["nombre_cliente"])
        if not cliente_res.get("ok"):
            return cliente_res

        cliente = cliente_res["cliente"]
        if self.es_cliente and self.id_cliente and cliente["id"] != self.id_cliente:
            return {"ok": False, "error": "Solo puedes agendar citas para tus vehículos."}

        vehiculo_res = cita_service.find_vehiculo_por_referencia(
            placa=args.get("placa"),
            id_cliente=cliente["id"],
            modelo=args.get("modelo_vehiculo"),
        )
        if not vehiculo_res.get("ok"):
            return vehiculo_res

        mecanico_res = None
        isla_res = None
        if auto:
            try:
                defaults = cita_service.get_default_asignacion_taller(id_sucursal)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            mecanico_id = defaults["id_mecanico"]
            if self.es_mecanico and self.id_mecanico:
                mecanico_id = self.id_mecanico
            isla_id = forced_isla or defaults["id_isla"]
            mecanico_res = {"ok": True, "mecanico": {"id": mecanico_id, "nombre": "taller"}}
            isla_res = {"ok": True, "isla": {"id": isla_id, "nombre": "isla activa"}}
        else:
            mecanico_res = cita_service.find_mecanico_by_nombre(args["nombre_mecanico"], id_sucursal)
            if not mecanico_res.get("ok"):
                return mecanico_res
            isla_res = cita_service.find_isla_by_referencia(args["isla"], id_sucursal)
            if not isla_res.get("ok"):
                return isla_res

        servicios = args.get("servicios") or []
        if not servicios:
            tipos = catalog_service.list_tipos_mantenimiento(id_sucursal)
            if tipos:
                servicios = [tipos[0]["id"]]
            else:
                return {
                    "ok": False,
                    "error": "No hay servicios registrados. Crea al menos uno en el módulo Servicios.",
                    "recoverable": True,
                }
        fecha = args.get("fecha_cita") or "2026-06-11 09:00:00"
        cita_id = cita_service.create_cita({
            "id_cliente": cliente["id"],
            "id_vehiculo": vehiculo_res["vehiculo"]["id"],
            "id_sucursal": id_sucursal,
            "fecha_cita": fecha,
            "id_horario": None,
            "id_mecanico": mecanico_res["mecanico"]["id"],
            "id_isla": isla_res["isla"]["id"],
            "descripcion_fallo": args["descripcion_fallo"],
            "fecha_compromiso": fecha.split(" ")[0],
            "hora_compromiso": "18:00:00",
        }, servicios)
        return {
            "ok": True,
            "id_cita": cita_id,
            "cliente": cliente["nombre"],
            "placa": vehiculo_res["vehiculo"]["placa"],
            "mecanico": mecanico_res["mecanico"]["nombre"],
            "isla": isla_res["isla"]["nombre"],
            "mensaje": "Cita creada correctamente",
        }

    def _buscar_cliente(self, args: dict) -> dict:
        return cita_service.find_cliente_by_nombre(args["nombre"])

    def _buscar_vehiculo(self, args: dict) -> dict:
        return cita_service.find_vehiculo_por_referencia(
            placa=args.get("placa"),
            id_cliente=args.get("id_cliente"),
            modelo=args.get("modelo"),
            id_sucursal=args.get("id_sucursal"),
            id_mecanico_asignado=args.get("id_mecanico_asignado"),
        )

    def _cambiar_estado_cita_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        id_sucursal = args.get("id_sucursal", DEFAULT_SUCURSAL_ID)
        id_cita = args.get("id_cita")

        if not id_cita and args.get("placa"):
            cita_res = cita_service.find_cita_activa_por_placa(
                args["placa"],
                id_sucursal,
                args.get("id_cliente"),
                args.get("id_mecanico"),
            )
            if not cita_res.get("ok"):
                return cita_res
            id_cita = cita_res["cita"]["id"]

        if not id_cita:
            return {"ok": False, "error": "Indica placa o id_cita."}

        denied = self._assert_cita_del_mecanico(id_cita)
        if denied:
            return denied

        return self._cambiar_estado_cita({"id_cita": id_cita, "estado": args["estado"]})

    def _cancelar_cita_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        id_sucursal = args.get("id_sucursal", DEFAULT_SUCURSAL_ID)
        id_cita = args.get("id_cita")

        if not id_cita and args.get("placa"):
            cita_res = cita_service.find_cita_activa_por_placa(
                args["placa"],
                id_sucursal,
                args.get("id_cliente"),
                args.get("id_mecanico"),
            )
            if not cita_res.get("ok"):
                return cita_res
            id_cita = cita_res["cita"]["id"]

        if not id_cita:
            return {"ok": False, "error": "Indica la placa o el id de la cita a cancelar."}

        denied = self._assert_cita_del_cliente(id_cita)
        if denied:
            return denied

        return cita_service.cancelar_cita(id_cita)

    def _editar_cita_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        id_sucursal = args.get("id_sucursal", DEFAULT_SUCURSAL_ID)
        id_cita = args.get("id_cita")

        if not id_cita and args.get("placa"):
            cita_res = cita_service.find_cita_activa_por_placa(args["placa"], id_sucursal)
            if not cita_res.get("ok"):
                return cita_res
            id_cita = cita_res["cita"]["id"]

        if not id_cita:
            return {"ok": False, "error": "Indica la placa o el id de la cita a editar."}

        updates: dict = {}
        if args.get("descripcion_fallo"):
            updates["descripcion_fallo"] = args["descripcion_fallo"]
        if args.get("nombre_mecanico"):
            mecanico_res = cita_service.find_mecanico_by_nombre(args["nombre_mecanico"], id_sucursal)
            if not mecanico_res.get("ok"):
                return mecanico_res
            updates["id_mecanico"] = mecanico_res["mecanico"]["id"]
        if args.get("isla"):
            isla_res = cita_service.find_isla_by_referencia(args["isla"], id_sucursal)
            if not isla_res.get("ok"):
                return isla_res
            updates["id_isla"] = isla_res["isla"]["id"]
        if args.get("fecha_cita"):
            updates["fecha_cita"] = args["fecha_cita"]
        if args.get("fecha_compromiso"):
            updates["fecha_compromiso"] = args["fecha_compromiso"]
        if args.get("hora_compromiso"):
            updates["hora_compromiso"] = args["hora_compromiso"]

        return cita_service.update_cita(id_cita, updates)

    def _buscar_fallas_similares(self, args: dict) -> dict:
        if not self.rag:
            return {"error": "RAG no activo en este modo"}
        limite = args.get("limite", 5)
        if self.es_propietario and self.id_sucursal:
            id_sucursal = args.get("id_sucursal") or self.id_sucursal
            id_mecanico = None
        else:
            id_sucursal = args.get("id_sucursal") if self.es_mecanico else None
            id_mecanico = args.get("id_mecanico") if self.es_mecanico else None
        result = self.rag.search_similar(
            args["descripcion"],
            n_results=limite,
            id_sucursal=id_sucursal,
            id_mecanico=id_mecanico,
        )
        if not self.es_mecanico or not self.id_mecanico:
            return result
        # Refuerzo: solo citas del mecánico (cubre docs viejos sin metadata).
        citas = cita_service.list_citas(
            id_sucursal or self.id_sucursal,
            id_mecanico=self.id_mecanico,
        )
        cita_ids = {str(c["id"]) for c in citas}
        placas = {cita_service._norm_placa(c.get("placa") or "") for c in citas if c.get("placa")}
        filtered = []
        for m in result.get("matches") or []:
            id_cita = str(m.get("id_cita") or "")
            placa = cita_service._norm_placa(m.get("placa") or "")
            if (id_cita and id_cita in cita_ids) or (placa and placa in placas):
                filtered.append(m)
        return {**result, "matches": filtered}

    def _cambiar_estado_cita(self, args: dict) -> dict:
        denied = self._assert_cita_del_mecanico(args["id_cita"])
        if denied:
            return denied
        return cita_service.cambiar_estado_cita(args["id_cita"], args["estado"])

