"""JWT RS256 — autenticación stateless con claims de rol y sucursal."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

import jwt

from config import BASE_DIR, IS_PRODUCTION, SESSION_COOKIE_MAX_AGE

_KEYS_DIR = BASE_DIR / "data" / "keys"
_PRIVATE_PATH = _KEYS_DIR / "jwt_private.pem"
_PUBLIC_PATH = _KEYS_DIR / "jwt_public.pem"
_ALGORITHM = "RS256"
_ISSUER = "iespro-taller"


def _load_pem_from_env(name: str) -> str | None:
  value = os.getenv(name, "").strip()
  if not value:
    return None
  return value.replace("\\n", "\n")


def _ensure_keypair() -> tuple[str, str]:
  env_priv = _load_pem_from_env("JWT_PRIVATE_KEY_PEM")
  env_pub = _load_pem_from_env("JWT_PUBLIC_KEY_PEM")
  if env_priv and env_pub:
    return env_priv, env_pub

  if _PRIVATE_PATH.is_file() and _PUBLIC_PATH.is_file():
    return _PRIVATE_PATH.read_text(), _PUBLIC_PATH.read_text()

  if IS_PRODUCTION:
    raise RuntimeError(
      "Faltan claves JWT en producción (JWT_PRIVATE_KEY_PEM / JWT_PUBLIC_KEY_PEM o data/keys/*.pem)"
    )

  from cryptography.hazmat.primitives import serialization
  from cryptography.hazmat.primitives.asymmetric import rsa

  _KEYS_DIR.mkdir(parents=True, exist_ok=True)
  key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
  private_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
  ).decode()
  public_pem = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
  ).decode()
  _PRIVATE_PATH.write_text(private_pem)
  _PUBLIC_PATH.write_text(public_pem)
  return private_pem, public_pem


_PRIVATE_KEY: str | None = None
_PUBLIC_KEY: str | None = None


def _keys() -> tuple[str, str]:
  global _PRIVATE_KEY, _PUBLIC_KEY
  if _PRIVATE_KEY is None or _PUBLIC_KEY is None:
    _PRIVATE_KEY, _PUBLIC_KEY = _ensure_keypair()
  return _PRIVATE_KEY, _PUBLIC_KEY


def issue_session_token(
  *,
  user_id: int,
  rol: str,
  sucursal_id: int | None,
  session_id: str | None = None,
) -> tuple[str, str]:
  """Devuelve (jwt, session_id/jti)."""
  jti = session_id or str(uuid.uuid4())
  now = int(time.time())
  payload = {
    "iss": _ISSUER,
    "sub": str(user_id),
    "rol": rol or "",
    "sucursal": sucursal_id,
    "jti": jti,
    "iat": now,
    "exp": now + SESSION_COOKIE_MAX_AGE,
  }
  private_key, _ = _keys()
  token = jwt.encode(payload, private_key, algorithm=_ALGORITHM)
  return token, jti


def decode_session_token(token: str) -> dict[str, Any]:
  _, public_key = _keys()
  return jwt.decode(
    token,
    public_key,
    algorithms=[_ALGORITHM],
    issuer=_ISSUER,
    options={"require": ["exp", "iat", "sub", "jti", "rol"]},
  )
