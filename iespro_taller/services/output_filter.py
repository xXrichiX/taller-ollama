"""Filtrado de salida del LLM (PII, tokens, rutas internas)."""

from __future__ import annotations

import re

from config import IS_PRODUCTION

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?52)?\s*\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b")
_INTERNAL_RE = re.compile(
  r"\b(tool_calls?|pipeline|fetch_k|rerank|ttft_ms|route|jti|jwt|mysql|chromadb)\b",
  re.I,
)


def filter_llm_output(text: str) -> str:
  if not text:
    return ""
  cleaned = text
  if IS_PRODUCTION:
    cleaned = _EMAIL_RE.sub("[correo oculto]", cleaned)
    cleaned = _PHONE_RE.sub("[teléfono oculto]", cleaned)
    cleaned = _INTERNAL_RE.sub("[filtrado]", cleaned)
  return cleaned.strip()
