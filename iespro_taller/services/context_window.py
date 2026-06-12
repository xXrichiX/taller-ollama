"""Gestión de ventana de contexto para el historial enviado a Ollama.

Estrategia: ventana deslizante por tokens + resumen determinista de turnos
descartados (sin segunda llamada al LLM).
"""

from __future__ import annotations

from typing import Any

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _message_tokens(msg: dict[str, Any]) -> int:
    return estimate_tokens(str(msg.get("content") or ""))


def summarize_dropped_messages(messages: list[dict[str, str]]) -> str:
    """Condensa turnos antiguos en un bloque breve para no perder el hilo."""
    if not messages:
        return ""

    lines: list[str] = []
    for msg in messages:
        role = "Usuario" if msg.get("role") == "user" else "Asistente"
        texto = (msg.get("content") or "").strip().replace("\n", " ")
        if len(texto) > 140:
            texto = texto[:137] + "..."
        if texto:
            lines.append(f"- {role}: {texto}")

    if not lines:
        return ""

    return (
        "Resumen de mensajes anteriores de esta conversación "
        "(los turnos completos se omitieron por límite de contexto):\n"
        + "\n".join(lines)
    )


def trim_messages_for_context(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    reserved_tokens: int = 0,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Recorta el historial conservando los turnos más recientes dentro del presupuesto.

    Returns:
        (mensajes_para_ollama, metadatos_de_auditoría)
    """
    budget = max(256, max_tokens - reserved_tokens)
    meta: dict[str, Any] = {
        "budget_tokens": budget,
        "input_messages": len(messages),
        "dropped_messages": 0,
        "used_tokens": 0,
        "summarized": False,
    }

    if not messages:
        return [], meta

    kept: list[dict[str, str]] = []
    used = 0
    drop_index = 0

    for idx in range(len(messages) - 1, -1, -1):
        cost = _message_tokens(messages[idx])
        if kept and used + cost > budget:
            drop_index = idx + 1
            break
        if not kept and cost > budget:
            # Mensaje único demasiado largo: se trunca en lugar de vaciar contexto.
            content = (messages[idx].get("content") or "")[: budget * _CHARS_PER_TOKEN]
            kept.insert(0, {"role": messages[idx]["role"], "content": content})
            used = _message_tokens(kept[0])
            drop_index = idx
            break
        kept.insert(0, messages[idx])
        used += cost
    else:
        drop_index = 0

    dropped = messages[:drop_index]
    meta["dropped_messages"] = len(dropped)

    if dropped:
        summary = summarize_dropped_messages(dropped)
        if summary:
            summary_msg = {"role": "system", "content": summary}
            summary_cost = _message_tokens(summary_msg)
            while kept and used + summary_cost > budget:
                removed = kept.pop(0)
                used -= _message_tokens(removed)
            if used + summary_cost <= budget:
                kept.insert(0, summary_msg)
                used += summary_cost
                meta["summarized"] = True

    meta["output_messages"] = len(kept)
    meta["used_tokens"] = used
    return kept, meta
