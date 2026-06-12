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


class ToolsService:
    def __init__(self, rag_service=None):
        self.rag = rag_service
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
        try:
            result = self._handlers[name](arguments or {})
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

    def _contar_citas(self, args: dict) -> dict:
        total = cita_service.count_citas(args.get("estado"), args.get("id_sucursal"))
        return {"total": total, "estado": args.get("estado"), "id_sucursal": args.get("id_sucursal")}

    def _listar_citas(self, args: dict) -> list[dict]:
        citas = cita_service.list_citas(args.get("id_sucursal"))
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
        vehiculo_res = cita_service.find_vehiculo_por_referencia(
            placa=args.get("placa"),
            id_cliente=cliente["id"],
            modelo=args.get("modelo_vehiculo"),
        )
        if not vehiculo_res.get("ok"):
            return vehiculo_res

        mecanico_res = cita_service.find_mecanico_by_nombre(args["nombre_mecanico"], id_sucursal)
        if not mecanico_res.get("ok"):
            return mecanico_res

        isla_res = cita_service.find_isla_by_referencia(args["isla"], id_sucursal)
        if not isla_res.get("ok"):
            return isla_res

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
            cita_res = cita_service.find_cita_activa_por_placa(args["placa"], id_sucursal)
            if not cita_res.get("ok"):
                return cita_res
            id_cita = cita_res["cita"]["id"]

        if not id_cita:
            return {"ok": False, "error": "Indica placa o id_cita."}

        return self._cambiar_estado_cita({"id_cita": id_cita, "estado": args["estado"]})

    def _buscar_fallas_similares(self, args: dict) -> dict:
        if not self.rag:
            return {"error": "RAG no activo en este modo"}
        limite = args.get("limite", 5)
        return self.rag.search_similar(args["descripcion"], n_results=limite)

    def _cambiar_estado_cita(self, args: dict) -> dict:
        from db.connection import execute

        execute(
            "UPDATE citas SET estado = %s WHERE id = %s",
            (args["estado"], args["id_cita"]),
        )
        return {"ok": True, "id_cita": args["id_cita"], "nuevo_estado": args["estado"]}


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
