"""Resiliencia de function calling: respuestas seguras y anti-bucles."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

MAX_TOOL_ERROR_CHARS = 220
RETRY_GUARD_MESSAGE = (
    "No reintentes la misma herramienta con los mismos parámetros. "
    "Explica el problema al usuario en español claro y pide los datos que falten."
)


def is_tool_failure(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("error"):
        return True
    return result.get("ok") is False


def sanitize_tool_result(name: str, result: Any, *, exc: Exception | None = None) -> dict[str, Any]:
    """Normaliza éxito/error sin exponer trazas largas al modelo."""
    if exc is not None:
        logger.warning("Tool %s falló: %s", name, exc)
        return {
            "ok": False,
            "tool": name,
            "error": str(exc)[:MAX_TOOL_ERROR_CHARS],
            "recoverable": True,
        }

    if isinstance(result, dict) and is_tool_failure(result):
        error = str(result.get("error") or "Error desconocido")[:MAX_TOOL_ERROR_CHARS]
        logger.info("Tool %s devolvió error controlado: %s", name, error)
        return {
            "ok": False,
            "tool": name,
            "error": error,
            "recoverable": True,
        }

    return {"ok": True, "tool": name, "result": result}


def tool_message_content(name: str, result: Any) -> str:
    """Payload JSON seguro para role=tool (evita envenenar memoria del turno)."""
    if isinstance(result, dict) and is_tool_failure(result):
        payload = {
            "ok": False,
            "tool": name,
            "error": str(result.get("error") or "Error desconocido")[:MAX_TOOL_ERROR_CHARS],
            "instruction": RETRY_GUARD_MESSAGE,
        }
    else:
        payload = sanitize_tool_result(name, result)
    return json.dumps(payload, ensure_ascii=False, default=str)


def tool_failure_user_message(tool_calls_log: list[dict[str, Any]]) -> str:
    """Mensaje amigable al usuario cuando todas las tools fallan en el turno."""
    from services.tool_response_format import format_tool_result

    errors: list[str] = []
    for entry in tool_calls_log:
        text = format_tool_result(entry.get("name", ""), entry.get("result"))
        if text:
            errors.append(text.strip())

    if not errors:
        return (
            "No pude hacer eso todavía. "
            "Dime cliente, placa, mecánico, isla y qué falla tiene el vehículo."
        )

    detalle = errors[0] if len(errors) == 1 else "\n".join(f"- {e}" for e in errors)
    combined = " ".join(errors).lower()

    if any(k in combined for k in ("placa", "modelo", "vehículo", "vehiculo", "cliente")):
        return (
            "Claro, te ayudo a agendar la cita, pero me faltan algunos datos.\n\n"
            f"{detalle}\n\n"
            "Puedes decirlo así:\n"
            "Crea una cita para Roberto García, placa ABC-123, mecánico Carlos, "
            "isla 1, falla: ruido en frenos."
        )

    if "cita" in combined:
        return f"No pude actualizar la cita. {detalle}\n\nIndica la placa o el id de la cita."

    return detalle


def should_skip_followup_llm(tool_calls_log: list[dict[str, Any]]) -> bool:
    """Si todo falló, no mandamos otro chat a Ollama con errores en el buffer."""
    if not tool_calls_log:
        return False
    return all(is_tool_failure(entry.get("result")) for entry in tool_calls_log)


def call_signature(name: str | None, args: dict | None) -> str:
    try:
        return json.dumps({"name": name, "args": args or {}}, sort_keys=True, default=str)
    except TypeError:
        return f"{name}:{args}"
