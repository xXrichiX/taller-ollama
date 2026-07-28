"""Validación de configuración obligatoria en producción."""

from __future__ import annotations

import os

from config import (
  IS_PRODUCTION,
  MAX_TOOL_CALLS_PER_TURN,
  MYSQL_PASSWORD,
  MYSQL_USER,
  SESSION_IDLE_SECONDS,
  TRUST_PROXY_HEADERS,
)


def validate_production_config() -> None:
  if not IS_PRODUCTION:
    return

  errors: list[str] = []

  if MYSQL_USER == "root":
    errors.append("MYSQL_USER no debe ser 'root' (usa MYSQL_USER=iespro_app)")

  if not MYSQL_PASSWORD or len(MYSQL_PASSWORD) < 16:
    errors.append("MYSQL_PASSWORD debe tener al menos 16 caracteres")

  if not TRUST_PROXY_HEADERS:
    errors.append("TRUST_PROXY_HEADERS debe ser 1 detrás de Caddy/nginx")

  if SESSION_IDLE_SECONDS < 300:
    errors.append("SESSION_IDLE_SECONDS demasiado bajo para operación estable")

  if MAX_TOOL_CALLS_PER_TURN < 1 or MAX_TOOL_CALLS_PER_TURN > 20:
    errors.append("MAX_TOOL_CALLS_PER_TURN debe estar entre 1 y 20")

  from pathlib import Path
  from config import BASE_DIR

  has_jwt_env = bool(os.getenv("JWT_PRIVATE_KEY_PEM", "").strip())
  has_jwt_files = (BASE_DIR / "data" / "keys" / "jwt_private.pem").is_file()
  if not has_jwt_env and not has_jwt_files:
    errors.append("Faltan claves JWT (JWT_PRIVATE_KEY_PEM o data/keys/*.pem)")

  if errors:
    raise RuntimeError(
      "Configuración de seguridad de producción inválida: " + "; ".join(errors)
    )
