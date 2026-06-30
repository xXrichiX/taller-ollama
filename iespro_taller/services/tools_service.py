import json
from typing import Any, Callable

from services import cita_service, catalog_service


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
            "name": "crear_cita_natural",
            "description": (
                "Crea una cita usando nombres y placa (NO pidas IDs al usuario). "
                "Resuelve cliente, vehículo, mecánico e isla en el backend."
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
                },
                "required": [
                    "nombre_cliente",
                    "descripcion_fallo",
                    "nombre_mecanico",
                    "isla",
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
    "mecanicos_en_isla",
    "cambiar_estado_cita_natural",
    "cambiar_estado_cita",
    "editar_cita_natural",
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
    ):
        self.rag = rag_service
        self.id_cliente = id_cliente
        self.nombre_cliente = nombre_cliente
        self.es_cliente = es_cliente
        self.id_mecanico = id_mecanico
        self.es_mecanico = es_mecanico
        self._handlers: dict[str, Callable[[dict], Any]] = {
            "contar_citas": self._contar_citas,
            "listar_citas": self._listar_citas,
            "listar_clientes": self._listar_clientes,
            "listar_vehiculos": self._listar_vehiculos,
            "listar_mecanicos": self._listar_mecanicos,
            "crear_cita_natural": self._crear_cita_natural,
            "buscar_cliente": self._buscar_cliente,
            "buscar_vehiculo": self._buscar_vehiculo,
            "cambiar_estado_cita_natural": self._cambiar_estado_cita_natural,
            "cancelar_cita_natural": self._cancelar_cita_natural,
            "editar_cita_natural": self._editar_cita_natural,
            "mecanicos_en_isla": self._mecanicos_en_isla,
            "listar_islas": self._listar_islas,
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
        if self.es_mecanico and name in MECANICO_DENIED_TOOLS:
            return {
                "ok": False,
                "error": "Como mecánico solo puedes consultar y actualizar estado de tus citas asignadas.",
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
            if name == "crear_cita_natural" and self.nombre_cliente:
                scoped["nombre_cliente"] = self.nombre_cliente
                scoped.setdefault("asignacion_automatica", True)
            if name in ("cancelar_cita_natural",) and scoped.get("placa"):
                scoped["id_cliente"] = self.id_cliente
            return scoped
        if self.es_mecanico and self.id_mecanico:
            if name in ("cancelar_cita_natural", "cambiar_estado_cita_natural") and scoped.get("placa"):
                scoped["id_mecanico"] = self.id_mecanico
        return scoped

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
        if not self.es_mecanico or not self.id_mecanico:
            return None
        cita = cita_service.get_cita_by_id(id_cita)
        if not cita:
            return {"ok": False, "error": "Cita no encontrada."}
        if cita.get("id_mecanico") != self.id_mecanico:
            return {"ok": False, "error": "Solo puedes gestionar citas asignadas a ti."}
        return None

    def _contar_citas(self, args: dict) -> dict:
        total = cita_service.count_citas(
            args.get("estado"),
            args.get("id_sucursal"),
            args.get("id_cliente"),
            args.get("id_mecanico"),
        )
        return {"total": total, "estado": args.get("estado"), "id_sucursal": args.get("id_sucursal")}

    def _listar_citas(self, args: dict) -> list[dict]:
        citas = cita_service.list_citas(
            args.get("id_sucursal"),
            args.get("id_cliente"),
            args.get("id_mecanico"),
        )
        return citas[:15]

    def _mecanicos_en_isla(self, args: dict) -> list[dict]:
        return cita_service.get_mecanicos_por_isla(args["id_isla"])

    def _listar_islas(self, args: dict) -> list[dict]:
        return cita_service.list_islas(args["id_sucursal"])

    def _vehiculos_de_cliente(self, args: dict) -> list[dict]:
        return cita_service.list_vehiculos(args["id_cliente"])

    def _listar_clientes(self, args: dict) -> list[dict]:
        return catalog_service.list_clientes()

    def _listar_vehiculos(self, args: dict) -> list[dict]:
        return cita_service.list_vehiculos(args.get("id_cliente"))

    def _listar_mecanicos(self, args: dict) -> list[dict]:
        return cita_service.list_mecanicos(args.get("id_sucursal", 1))

    def _crear_cita_natural(self, args: dict) -> dict:
        from config import DEFAULT_SUCURSAL_ID

        id_sucursal = args.get("id_sucursal", DEFAULT_SUCURSAL_ID)

        if not args.get("placa") and not args.get("modelo_vehiculo"):
            return {"ok": False, "error": "Indica placa o modelo del vehículo."}

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
        if args.get("asignacion_automatica"):
            try:
                defaults = cita_service.get_default_asignacion_taller(id_sucursal)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            mecanico_res = {"ok": True, "mecanico": {"id": defaults["id_mecanico"], "nombre": "asignación pendiente"}}
            isla_res = {"ok": True, "isla": {"id": defaults["id_isla"], "nombre": "asignación pendiente"}}
        else:
            mecanico_res = cita_service.find_mecanico_by_nombre(args["nombre_mecanico"], id_sucursal)
            if not mecanico_res.get("ok"):
                return mecanico_res
            isla_res = cita_service.find_isla_by_referencia(args["isla"], id_sucursal)
            if not isla_res.get("ok"):
                return isla_res

        if not args.get("nombre_mecanico") and not args.get("asignacion_automatica"):
            return {"ok": False, "error": "Indica el mecánico para la cita."}
        if not args.get("isla") and not args.get("asignacion_automatica"):
            return {"ok": False, "error": "Indica la isla para la cita."}

        servicios = args.get("servicios") or [4]
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
        return self.rag.search_similar(args["descripcion"], n_results=limite)

    def _cambiar_estado_cita(self, args: dict) -> dict:
        denied = self._assert_cita_del_mecanico(args["id_cita"])
        if denied:
            return denied
        return cita_service.cambiar_estado_cita(args["id_cita"], args["estado"])


def run_sql_query(question: str, id_sucursal: int) -> str | None:
    q = question.lower()
    if "cuántas citas" in q or "cuantas citas" in q or "total de citas" in q:
        if "pendiente" in q:
            total = cita_service.count_citas("PENDIENTE", id_sucursal)
            return f"Hay {total} citas pendientes en la sucursal {id_sucursal}."
        if "proceso" in q:
            total = cita_service.count_citas("EN_PROCESO", id_sucursal)
            return f"Hay {total} citas en proceso."
        total = cita_service.count_citas(None, id_sucursal)
        return f"Hay {total} citas registradas en total."

    if "clientes" in q and ("cuántos" in q or "cuantos" in q or "total" in q):
        clientes = catalog_service.list_clientes()
        return f"Hay {len(clientes)} clientes registrados."

    if "vehículos" in q or "vehiculos" in q:
        if "cuántos" in q or "cuantos" in q or "total" in q:
            vehiculos = cita_service.list_vehiculos()
            return f"Hay {len(vehiculos)} vehículos registrados."

    return None
