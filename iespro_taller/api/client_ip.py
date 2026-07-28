"""IP del cliente detrás de proxy (Caddy/nginx)."""

from __future__ import annotations

from starlette.requests import Request

from config import TRUST_PROXY_HEADERS


def get_client_ip(request: Request) -> str:
  if TRUST_PROXY_HEADERS:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
      return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
      return real_ip
  if request.client and request.client.host:
    return request.client.host
  return "127.0.0.1"
