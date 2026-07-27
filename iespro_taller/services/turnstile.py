"""Verificación Cloudflare Turnstile (opcional)."""

from __future__ import annotations

import httpx

from config import TURNSTILE_SECRET_KEY


def turnstile_enabled() -> bool:
  return bool(TURNSTILE_SECRET_KEY)


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
  if not TURNSTILE_SECRET_KEY:
    return True
  if not (token or "").strip():
    return False
  data: dict[str, str] = {
    "secret": TURNSTILE_SECRET_KEY,
    "response": token.strip(),
  }
  if remote_ip:
    data["remoteip"] = remote_ip
  try:
    with httpx.Client(timeout=10.0) as client:
      res = client.post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=data,
      )
      res.raise_for_status()
      return bool(res.json().get("success"))
  except Exception:
    return False
