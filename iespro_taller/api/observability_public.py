"""Respuestas de observabilidad sin exponer prompts completos en producción."""

from __future__ import annotations

from typing import Any


def _redact_text(text: str | None, limit: int = 80) -> str:
  raw = (text or "").strip()
  if not raw:
    return ""
  if len(raw) <= limit:
    return raw
  return raw[:limit] + "… [redactado]"


def public_observability_logs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
  sanitized: list[dict[str, Any]] = []
  for row in rows:
    item = dict(row)
    item["user_prompt"] = _redact_text(str(item.get("user_prompt") or ""))
    item["system_response"] = _redact_text(str(item.get("system_response") or ""), limit=120)
    tools = item.get("tools_executed")
    if isinstance(tools, str):
      item["tools_executed"] = "[redactado]" if tools else []
    elif isinstance(tools, list) and tools:
      item["tools_executed"] = [{"name": t.get("name", "tool")} for t in tools if isinstance(t, dict)]
    sanitized.append(item)
  return sanitized
