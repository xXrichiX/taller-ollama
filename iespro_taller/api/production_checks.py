"""Validación de configuración obligatoria en producción."""

from __future__ import annotations

import os

from config import (
  APP_ENV,
  AUDIT_HMAC_SECRET,
  EMAIL_VERIFICATION_SECRET,
  IS_PRODUCTION,
  MAX_TOOL_CALLS_PER_TURN,
  METRICS_TOKEN,
  MYSQL_PASSWORD,
  MYSQL_USER,
  REGISTRATION_ENABLED,
  SESSION_IDLE_SECONDS,
  SESSION_STORE,
  SMTP_FROM,
  SMTP_HOST,
  TRUST_PROXY_HEADERS,
  TURNSTILE_SECRET_KEY,
  TURNSTILE_SITE_KEY,
)


def validate_production_config() -> None:
  if not IS_PRODUCTION:
    return

  errors: list[str] = []

  if APP_ENV not in ("production", "prod"):
    errors.append(f"APP_ENV debe ser production (actual: {APP_ENV!r})")

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

  if not AUDIT_HMAC_SECRET or len(AUDIT_HMAC_SECRET) < 32:
    errors.append("AUDIT_HMAC_SECRET debe tener al menos 32 caracteres en producción")

  if not METRICS_TOKEN or len(METRICS_TOKEN) < 32:
    errors.append("METRICS_TOKEN debe configurarse en producción (protege /metrics)")

  if REGISTRATION_ENABLED and (not TURNSTILE_SECRET_KEY or not TURNSTILE_SITE_KEY):
    errors.append(
      "REGISTRATION_ENABLED=1 exige TURNSTILE_SITE_KEY y TURNSTILE_SECRET_KEY en producción"
    )

  if IS_PRODUCTION and SESSION_STORE != "mysql":
    errors.append("SESSION_STORE debe ser 'mysql' en producción")

  if REGISTRATION_ENABLED:
    if not SMTP_HOST or not SMTP_FROM:
      errors.append("REGISTRATION_ENABLED=1 exige SMTP_HOST y SMTP_FROM en producción")
    if not EMAIL_VERIFICATION_SECRET or len(EMAIL_VERIFICATION_SECRET) < 32:
      errors.append(
        "EMAIL_VERIFICATION_SECRET debe tener al menos 32 caracteres cuando el registro está habilitado"
      )

  if errors:
    raise RuntimeError(
      "Configuración de seguridad de producción inválida: " + "; ".join(errors)
    )
