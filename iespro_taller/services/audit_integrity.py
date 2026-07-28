"""Integridad HMAC de registros de auditoría (detección de alteración)."""

from __future__ import annotations

import hashlib
import hmac
import os


def audit_hmac_secret() -> bytes:
  raw = os.getenv("AUDIT_HMAC_SECRET", "").strip()
  if raw:
    return raw.encode("utf-8")
  if os.getenv("APP_ENV", "development").lower() in ("production", "prod"):
    raw = os.getenv("MYSQL_APP_PASSWORD") or os.getenv("MYSQL_PASSWORD") or ""
    if len(raw) >= 16:
      return f"audit:{raw}".encode("utf-8")
  return b"iespro-audit-dev-only"


def compute_integrity_hash(
  *,
  id_usuario: int | None,
  accion: str,
  recurso: str | None,
  detalle: str | None,
  ip: str | None,
  user_agent: str | None,
  resultado: str,
) -> str:
  payload = "|".join(
    [
      str(id_usuario if id_usuario is not None else ""),
      accion or "",
      recurso or "",
      detalle or "",
      ip or "",
      user_agent or "",
      resultado or "",
    ]
  )
  return hmac.new(audit_hmac_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_integrity_hash(row: dict) -> bool:
  expected = compute_integrity_hash(
    id_usuario=row.get("id_usuario"),
    accion=str(row.get("accion") or ""),
    recurso=row.get("recurso"),
    detalle=row.get("detalle"),
    ip=row.get("ip"),
    user_agent=row.get("user_agent"),
    resultado=str(row.get("resultado") or "ok"),
  )
  stored = str(row.get("integrity_hash") or "")
  if not stored:
    return False
  return hmac.compare_digest(stored, expected)
