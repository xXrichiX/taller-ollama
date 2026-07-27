"""Hashing de contraseñas (bcrypt) con migración desde texto plano legacy."""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
  return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_bcrypt_hash(stored: str | None) -> bool:
  return bool(stored) and stored.startswith("$2")


def verify_password(plain: str, stored: str | None) -> bool:
  if not stored:
    return False
  if is_bcrypt_hash(stored):
    try:
      return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
      return False
  return plain == stored


def needs_rehash(stored: str | None) -> bool:
  return bool(stored) and not is_bcrypt_hash(stored)
