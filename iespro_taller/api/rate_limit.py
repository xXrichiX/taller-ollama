"""Rate limiting por IP (slowapi)."""

from __future__ import annotations

from config import RATE_LIMIT_ENABLED
from slowapi import Limiter

from api.client_ip import get_client_ip

limiter = Limiter(
  key_func=get_client_ip,
  enabled=RATE_LIMIT_ENABLED,
  default_limits=["120/minute"],
)


def rate_limit(rule: str):
  """Decorador que no-op si RATE_LIMIT_ENABLED=0 (tests locales)."""
  if RATE_LIMIT_ENABLED:
    return limiter.limit(rule)
  return lambda func: func
