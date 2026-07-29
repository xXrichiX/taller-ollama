"""Validación de campos de texto en CRUD (anti-XSS/SSTI/SQLi almacenado)."""

from __future__ import annotations

import re

from fastapi import HTTPException

from api.security_messages import bad_request

# Patrones que no deben persistirse en nombres/descripciones de catálogo.
_UNSAFE_TEXT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
  re.compile(p, re.IGNORECASE)
  for p in (
    r"<[^>]+>",  # etiquetas HTML
    r"<\s*script",
    r"onerror\s*=",
    r"javascript\s*:",
    r"\{\{",  # SSTI Jinja/Twig
    r"\}\}",
    r"\$\{",  # EL
    r"<%",  # ERB/JSP
    r"__class__",
    r"__mro__",
    r"__subclasses__",
    r";\s*--",  # SQL comment stacking
    r"'\s*;\s*",
    r'"\s*;\s*',
    r"\bunion\s+select\b",
    r"\bdrop\s+table\b",
    r"\bdelete\s+from\b",
    r"\binsert\s+into\b",
    r"\bupdate\s+.+\bset\b",
    r"<!ENTITY",
    r"file://",
  )
)

_MAX_CATALOG_NAME_LEN = 120
_MAX_CATALOG_DESC_LEN = 2000
_MAX_CATALOG_CODE_LEN = 40
_MAX_UNIT_LEN = 20
_MAX_CATALOG_PRICE = 100_000.0
_MAX_INVENTORY_QTY = 10_000.0


def _reject_unsafe_text(value: str, *, field_label: str) -> None:
  text = value.strip()
  if not text:
    return
  for pattern in _UNSAFE_TEXT_PATTERNS:
    if pattern.search(text):
      raise HTTPException(
        status_code=400,
        detail=bad_request(f"{field_label} contiene caracteres o patrones no permitidos."),
      )


def validate_catalog_name(value: str, *, field_label: str = "El nombre") -> str:
  text = (value or "").strip()
  if not text:
    raise HTTPException(status_code=400, detail=bad_request(f"{field_label} es requerido."))
  if len(text) > _MAX_CATALOG_NAME_LEN:
    raise HTTPException(
      status_code=400,
      detail=bad_request(f"{field_label} no puede exceder {_MAX_CATALOG_NAME_LEN} caracteres."),
    )
  _reject_unsafe_text(text, field_label=field_label)
  return text


def validate_catalog_description(value: str, *, field_label: str = "La descripción") -> str:
  text = (value or "").strip()
  if not text:
    return ""
  if len(text) > _MAX_CATALOG_DESC_LEN:
    raise HTTPException(
      status_code=400,
      detail=bad_request(f"{field_label} no puede exceder {_MAX_CATALOG_DESC_LEN} caracteres."),
    )
  _reject_unsafe_text(text, field_label=field_label)
  return text


def validate_catalog_code(value: str) -> str:
  text = (value or "").strip()
  if not text:
    return ""
  if len(text) > _MAX_CATALOG_CODE_LEN:
    raise HTTPException(
      status_code=400,
      detail=bad_request("El código no puede exceder 40 caracteres."),
    )
  _reject_unsafe_text(text, field_label="El código")
  return text


def validate_catalog_unit(value: str) -> str:
  text = (value or "").strip() or "pza"
  if len(text) > _MAX_UNIT_LEN:
    raise HTTPException(status_code=400, detail=bad_request("La unidad no puede exceder 20 caracteres."))
  _reject_unsafe_text(text, field_label="La unidad")
  return text


def validate_catalog_price(precio: float, *, field_label: str = "El precio") -> None:
  if precio < 0:
    raise HTTPException(status_code=400, detail=bad_request(f"{field_label} no puede ser negativo."))
  if precio > _MAX_CATALOG_PRICE:
    raise HTTPException(
      status_code=400,
      detail=bad_request(f"{field_label} excede el máximo permitido."),
    )


def validate_inventory_quantity(value: float, *, field_label: str) -> None:
  if value < 0:
    raise HTTPException(status_code=400, detail=bad_request(f"{field_label} no puede ser negativo."))
  if value > _MAX_INVENTORY_QTY:
    raise HTTPException(
      status_code=400,
      detail=bad_request(f"{field_label} excede el máximo permitido."),
    )


def validate_client_name(value: str) -> str:
  return validate_catalog_name(value, field_label="El nombre del cliente")


def validate_fields(*pairs: tuple[str, str]) -> None:
  """Uso interno/tests: valida lista de (valor, etiqueta)."""
  for value, label in pairs:
    _reject_unsafe_text(value, field_label=label)
