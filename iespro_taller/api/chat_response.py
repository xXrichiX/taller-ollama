"""Respuestas públicas del chat: oculta detalles internos en producción."""

from __future__ import annotations

from typing import Any

from config import IS_PRODUCTION


def public_chat_result(result: dict[str, Any]) -> dict[str, Any]:
  """Elimina route, tool_calls y metrics en producción."""
  payload: dict[str, Any] = {"answer": result.get("answer")}
  if not IS_PRODUCTION:
    payload["route"] = result.get("route")
    payload["tool_calls"] = result.get("tool_calls", [])
    payload["metrics"] = result.get("metrics", {})
  return payload


def public_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
  """Oculta rutas internas en el historial del chat."""
  if not IS_PRODUCTION:
    return messages
  return [{k: v for k, v in row.items() if k != "route"} for row in messages]
