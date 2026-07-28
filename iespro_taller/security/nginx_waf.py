"""Manifiesto WAF edge — reglas obligatorias en web/nginx.conf (verificable en CI)."""

from __future__ import annotations

from pathlib import Path

from config import PROJECT_ROOT

NGINX_CONF = PROJECT_ROOT / "web" / "nginx.conf"

# Directivas mínimas que definen la capa WAF self-hosted.
REQUIRED_WAF_MARKERS: tuple[str, ...] = (
  "limit_req_zone",
  "limit_conn_zone",
  "map $http_user_agent $bad_bot",
  "map $request_uri $bad_uri",
  "$bad_bot",
  "$bad_uri",
  "server_tokens off",
  "Content-Security-Policy",
  "location = /.env",
  "limit_req zone=api_auth",
  "limit_req zone=api_chat",
  "limit_req_status 429",
)


def load_nginx_conf() -> str:
  if not NGINX_CONF.is_file():
    return ""
  return NGINX_CONF.read_text(encoding="utf-8")


def verify_nginx_waf_config() -> dict[str, object]:
  """Devuelve estado verificable del WAF en nginx (sin depender de Cloudflare)."""
  text = load_nginx_conf()
  missing = [m for m in REQUIRED_WAF_MARKERS if m not in text]
  return {
    "implemented": len(missing) == 0,
    "config_path": str(NGINX_CONF.relative_to(PROJECT_ROOT)),
    "required_markers": len(REQUIRED_WAF_MARKERS),
    "missing_markers": missing,
    "features": {
      "rate_limit_auth": "limit_req zone=api_auth" in text,
      "rate_limit_chat": "limit_req zone=api_chat" in text,
      "rate_limit_api": "limit_req zone=api_general" in text,
      "bot_block": "$bad_bot" in text,
      "uri_block": "$bad_uri" in text,
      "conn_limit": "limit_conn conn_per_ip" in text,
      "csp": "Content-Security-Policy" in text,
      "sensitive_paths_404": "location = /.env" in text,
    },
  }
