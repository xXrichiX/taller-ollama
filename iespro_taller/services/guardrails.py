"""Guardrails contra prompt injection (Semana 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass


BLOCKED_MESSAGE = (
    "Tu solicitud fue bloqueada por seguridad. "
    "Reformula la pregunta sin intentar alterar las instrucciones del sistema."
)


@dataclass
class GuardrailResult:
    blocked: bool
    reason: str = ""
    rule_id: str = ""


_BLOCK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"\b(ignora|ignore)\b.{0,50}\b(instrucciones|instructions|anteriores|previous)\b",
            re.I,
        ),
    ),
    (
        "reveal_system_prompt",
        re.compile(
            r"\b(revela|muestra|show|print|dime)\b.{0,50}\b(system\s*prompt|prompt del sistema|instrucciones del sistema)\b",
            re.I,
        ),
    ),
    (
        "role_hijack",
        re.compile(
            r"\b(asume|actua|actúa|pretende|roleplay|from now on)\b.{0,50}\b(rol|role|admin|root|desarrollador)\b",
            re.I,
        ),
    ),
    (
        "jailbreak",
        re.compile(
            r"\b(do anything now|dan|jailbreak|sin restricciones|without restrictions|modo dios)\b",
            re.I,
        ),
    ),
]


def validate_user_prompt(prompt: str) -> GuardrailResult:
    text = (prompt or "").strip()
    if not text:
        return GuardrailResult(blocked=False)

    if len(text) > 5000:
        return GuardrailResult(True, BLOCKED_MESSAGE, "input_too_long")

    for rule_id, pattern in _BLOCK_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(True, BLOCKED_MESSAGE, rule_id)

    if re.search(r"(\b\w+\b)(?:\s+\1){5,}", text.lower()):
        return GuardrailResult(True, BLOCKED_MESSAGE, "abnormal_repetition")

    return GuardrailResult(blocked=False)
