"""Rate limiting por IP (slowapi)."""

from __future__ import annotations

from config import RATE_LIMIT_ENABLED
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)


def rate_limit(rule: str):
  """Decorador que no-op si RATE_LIMIT_ENABLED=0 (tests locales)."""
  if RATE_LIMIT_ENABLED:
    return limiter.limit(rule)
  return lambda func: func
