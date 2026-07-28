"""Mensajes de seguridad (anti-enumeración y respuestas genéricas en prod)."""

from __future__ import annotations

from config import IS_PRODUCTION

REGISTER_GENERIC_MESSAGE = (
  "Si el correo es válido, hemos procesado tu solicitud. "
  "Revisa tu bandeja o inicia sesión."
)

# Mensajes genéricos en producción (no revelan islas, sucursales, CAPTCHA, etc.)
_GENERIC_FORBIDDEN = "Acceso denegado."
_GENERIC_BAD_REQUEST = "Los datos proporcionados no son válidos."
_GENERIC_NOT_FOUND = "Recurso no encontrado."
_GENERIC_UNAUTHORIZED = "Credenciales incorrectas."
_GENERIC_SESSION = "Sesión inválida o expirada."
_GENERIC_CAPTCHA = "No se pudo completar la verificación."
_GENERIC_SETUP = "Completa la configuración requerida para continuar."
_GENERIC_LIMIT = "Límite de recursos alcanzado."
_GENERIC_TOOL = "No se pudo completar la operación."


def public_detail(dev_message: str, *, prod_message: str | None = None) -> str:
  """En producción devuelve mensaje genérico; en dev el mensaje detallado."""
  if IS_PRODUCTION:
    return prod_message or _GENERIC_BAD_REQUEST
  return dev_message


def forbidden(dev_message: str = "Sin permiso") -> str:
  return public_detail(dev_message, prod_message=_GENERIC_FORBIDDEN)


def bad_request(dev_message: str) -> str:
  return public_detail(dev_message, prod_message=_GENERIC_BAD_REQUEST)


def not_found(dev_message: str = "No encontrado") -> str:
  return public_detail(dev_message, prod_message=_GENERIC_NOT_FOUND)


def unauthorized(dev_message: str = "Credenciales incorrectas") -> str:
  return public_detail(dev_message, prod_message=_GENERIC_UNAUTHORIZED)


def session_error(dev_message: str = "Sesión inválida") -> str:
  return public_detail(dev_message, prod_message=_GENERIC_SESSION)


def captcha_failed() -> str:
  return _GENERIC_CAPTCHA if IS_PRODUCTION else "Verificación CAPTCHA fallida."


def setup_required(dev_message: str) -> str:
  return public_detail(dev_message, prod_message=_GENERIC_SETUP)


def resource_limit(dev_message: str) -> str:
  return public_detail(dev_message, prod_message=_GENERIC_LIMIT)


def tool_error(dev_message: str) -> str:
  return public_detail(dev_message, prod_message=_GENERIC_TOOL)


def stream_error(dev_message: str = "Error interno del chat") -> str:
  return public_detail(dev_message, prod_message="No se pudo procesar el mensaje.")
