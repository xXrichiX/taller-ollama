"""Política de seguridad para tools del asistente IA (RBAC + minimización de datos)."""

from __future__ import annotations

import copy
from typing import Any

from services.tools_service import TOOL_DEFINITIONS

from config import IS_PRODUCTION

# Tools que solo el dueño del taller puede invocar (datos sensibles / catálogo amplio).
PROPIETARIO_ONLY_TOOLS = frozenset({
    "listar_clientes",
    "buscar_cliente",
    "crear_servicio_natural",
})

# Tools de solo lectura que pueden devolver muchos registros.
LIST_TOOLS = frozenset({
    "listar_citas",
    "listar_clientes",
    "listar_vehiculos",
    "listar_mecanicos",
    "listar_islas",
    "listar_inventario",
    "mecanicos_en_isla",
    "vehiculos_de_cliente",
})

MAX_TOOL_LIST_ROWS = 10 if IS_PRODUCTION else 25

PII_FIELDS = frozenset({
    "email",
    "telefono",
    "usuario_email",
    "password",
    "password_hash",
})

# En listados masivos no exponer contacto; buscar_cliente (1 registro) sí puede incluirlo.
BULK_REDACT_TOOLS = frozenset({
    "listar_clientes",
    "listar_citas",
    "listar_vehiculos",
    "buscar_cliente",
    "vehiculos_de_cliente",
})


def is_tool_allowed(
    name: str,
    *,
    es_cliente: bool,
    es_mecanico: bool,
    es_propietario: bool,
) -> bool:
    """Misma política que ToolsService.execute, centralizada."""
    from services.tools_service import CLIENTE_DENIED_TOOLS, MECANICO_DENIED_TOOLS

    if es_cliente and name in CLIENTE_DENIED_TOOLS:
        return False
    if es_mecanico and not es_propietario and name in MECANICO_DENIED_TOOLS:
        return False
    if es_propietario and name in {"listar_mecanicos", "listar_islas", "mecanicos_en_isla"}:
        return False
    if name in PROPIETARIO_ONLY_TOOLS and not es_propietario:
        return False
    return True


def tools_for_session(
    *,
    es_cliente: bool,
    es_mecanico: bool,
    es_propietario: bool,
) -> list[dict]:
    """Catálogo de tools visible para el LLM según rol (defensa en profundidad)."""
    allowed: list[dict] = []
    for tool in TOOL_DEFINITIONS:
        name = tool.get("function", {}).get("name") or ""
        if is_tool_allowed(
            name,
            es_cliente=es_cliente,
            es_mecanico=es_mecanico,
            es_propietario=es_propietario,
        ):
            allowed.append(tool)
    return allowed


def _redact_row(row: dict, *, bulk: bool) -> dict:
    out = dict(row)
    force_pii = IS_PRODUCTION or bulk
    for key in PII_FIELDS:
        if key in out:
            if force_pii:
                out[key] = "[oculto]"
            elif key in ("usuario_email", "password", "password_hash"):
                out.pop(key, None)
    return out


def redact_tool_result(tool_name: str, result: Any) -> Any:
    """Minimiza PII en resultados antes de enviarlos al LLM o al usuario."""
    if result is None:
        return result

    bulk = tool_name in BULK_REDACT_TOOLS

    if isinstance(result, list):
        trimmed = result[:MAX_TOOL_LIST_ROWS]
        rows = [_redact_row(row, bulk=bulk) if isinstance(row, dict) else row for row in trimmed]
        if len(result) > MAX_TOOL_LIST_ROWS:
            return {
                "ok": True,
                "total": len(result),
                "mostrados": len(rows),
                "aviso": f"Solo se muestran los primeros {MAX_TOOL_LIST_ROWS} registros.",
                "items": rows,
            }
        return rows

    if isinstance(result, dict):
        if "items" in result and isinstance(result["items"], list):
            cloned = copy.deepcopy(result)
            cloned["items"] = redact_tool_result(tool_name, cloned["items"])
            return cloned
        if bulk or tool_name in BULK_REDACT_TOOLS or IS_PRODUCTION:
            return _redact_row(result, bulk=True)
        return {k: v for k, v in result.items() if k not in ("password", "password_hash", "usuario_email")}

    return result
