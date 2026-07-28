"""Filtrado de salida del LLM (PII, tokens, rutas internas)."""

from __future__ import annotations

import re

from config import IS_PRODUCTION

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?52)?\s*\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b")
_CURP_RE = re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.I)
_RFC_RE = re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", re.I)
_INTERNAL_RE = re.compile(
  r"\b(tool_calls?|pipeline|fetch_k|rerank|ttft_ms|route|jti|jwt|mysql|chromadb|"
  r"run_sql|id_sucursal|id_isla|HACKED|pentest|ollama|function_calling)\b",
  re.I,
)
_SCOPE_LEAK_RE = re.compile(
  r"\b(sucursal|isla|cita|cliente)\s+no\s+permitid[ao]|sin\s+permiso\s+para\s+esta\b",
  re.I,
)
_IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def filter_llm_output(text: str) -> str:
  if not text:
    return ""
  cleaned = text
  if IS_PRODUCTION:
    cleaned = _EMAIL_RE.sub("[correo oculto]", cleaned)
    cleaned = _PHONE_RE.sub("[teléfono oculto]", cleaned)
    cleaned = _CURP_RE.sub("[dato oculto]", cleaned)
    cleaned = _RFC_RE.sub("[dato oculto]", cleaned)
    cleaned = _IP_RE.sub("[ip oculta]", cleaned)
    cleaned = _INTERNAL_RE.sub("[filtrado]", cleaned)
    cleaned = _SCOPE_LEAK_RE.sub("Acceso denegado.", cleaned)
  return cleaned.strip()
