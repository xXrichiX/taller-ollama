"""CAPTCHA matemático simple (sin servicios externos)."""

from __future__ import annotations

import hashlib
import hmac
import os
import random
import time
from base64 import urlsafe_b64encode

_SECRET = os.getenv("CAPTCHA_SECRET", "iespro-taller-captcha-dev")
_TTL_SEC = 300


def _sign(payload: str) -> str:
  return hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:20]


def issue_challenge() -> tuple[str, str]:
  a, b = random.randint(1, 9), random.randint(1, 9)
  exp = int(time.time()) + _TTL_SEC
  payload = f"{a}:{b}:{exp}"
  token = urlsafe_b64encode(f"{payload}:{_sign(payload)}".encode()).decode()
  return token, f"¿Cuánto es {a} + {b}?"


def verify_challenge(token: str, answer: str) -> bool:
  if not token or answer is None:
    return False
  try:
    from base64 import urlsafe_b64decode

    raw = urlsafe_b64decode(token.encode()).decode()
    a_s, b_s, exp_s, sig = raw.rsplit(":", 3)
    if int(time.time()) > int(exp_s):
      return False
    payload = f"{a_s}:{b_s}:{exp_s}"
    if not hmac.compare_digest(sig, _sign(payload)):
      return False
    return int(str(answer).strip()) == int(a_s) + int(b_s)
  except Exception:
    return False
