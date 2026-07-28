"""Barrera final de seguridad LLM: entrada y salida sin fugas de datos."""

from __future__ import annotations

import re
from dataclasses import dataclass

from config import IS_PRODUCTION
from services.output_filter import filter_llm_output

SAFE_REFUSAL = (
  "No puedo mostrar esa información por políticas de seguridad del taller. "
  "Pregunta por citas, inventario o servicios de forma específica."
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?52)?\s*\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]+\b")
_SQL_RE = re.compile(
  r"\b(select|insert|update|delete|drop|union|grant)\b.{0,80}\b(from|into|table|usuarios|clientes)\b",
  re.I,
)
_SECRET_RE = re.compile(
  r"\b(password|contraseña|api[_\s-]?key|secret|token|bearer)\s*[:=]\s*\S+",
  re.I,
)
_BCRYPT_RE = re.compile(r"\$2[aby]\$\d{2}\$")
_CONN_RE = re.compile(r"\b(mysql|postgres|mongodb)(:\/\/|ql://)", re.I)
_BULK_PII_RE = re.compile(
  r"\b(correos?|emails?|tel[eé]fonos?|celulares?|whatsapp)\b.{0,40}\b(todos|todas|lista|listado)\b",
  re.I,
)


@dataclass(frozen=True)
class OutputSafetyResult:
  text: str
  blocked: bool
  reason: str = ""


def _count_matches(pattern: re.Pattern[str], text: str) -> int:
  return len(pattern.findall(text or ""))


def is_unsafe_output(text: str) -> tuple[bool, str]:
  """Detecta salidas que no deben mostrarse al usuario."""
  if not text or not IS_PRODUCTION:
    return False, ""

  if len(text) > 6000:
    return True, "output_too_long"

  if _SQL_RE.search(text):
    return True, "sql_leak"

  if _JWT_RE.search(text):
    return True, "jwt_leak"

  if _SECRET_RE.search(text) or _BCRYPT_RE.search(text):
    return True, "credential_leak"

  if _CONN_RE.search(text):
    return True, "connection_string"

  emails = _count_matches(_EMAIL_RE, text)
  phones = _count_matches(_PHONE_RE, text)
  if emails >= 1 or phones >= 2:
    return True, "pii_leak"

  if _BULK_PII_RE.search(text):
    return True, "bulk_pii"

  return False, ""


def enforce_llm_output(text: str) -> OutputSafetyResult:
  """Filtra PII/términos internos y bloquea salidas peligrosas en producción."""
  cleaned = filter_llm_output(text or "")
  unsafe, reason = is_unsafe_output(cleaned)
  if unsafe:
    return OutputSafetyResult(SAFE_REFUSAL, True, reason)
  return OutputSafetyResult(cleaned, False)
