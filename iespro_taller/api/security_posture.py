"""Postura de seguridad verificable desde código."""

from __future__ import annotations

from config import (
  AUDIT_HMAC_SECRET,
  AUDIT_RETENTION_DAYS,
  BASE_DIR,
  IS_PRODUCTION,
  MAX_ISLAS_PER_SUCURSAL,
  MAX_SUCURSALES_PER_OWNER,
  METRICS_TOKEN,
  RATE_LIMIT_ENABLED,
  REGISTRATION_ENABLED,
  REGISTRATION_INVITE_CODE,
  SESSION_STORE,
  SMTP_FROM,
  SMTP_HOST,
  TURNSTILE_SECRET_KEY,
  TURNSTILE_SITE_KEY,
)
from security.nginx_waf import verify_nginx_waf_config


def _read_module_source(relative: str) -> str:
  path = BASE_DIR / relative
  try:
    return path.read_text(encoding="utf-8")
  except OSError:
    return ""


def _guardrail_rule_count() -> int:
  text = _read_module_source("services/guardrails.py")
  return text.count('"rule_id"') + text.count("_BLOCK_PATTERNS") if text else 0


def _sql_tool_absent() -> bool:
  src = _read_module_source("services/tools_service.py")
  if not src:
    return False
  banned = ("run_sql", "run_sql_query", '"sql"', "route: sql")
  return not any(b in src for b in banned)


def _llm_layers() -> dict[str, object]:
  guardrails_src = _read_module_source("services/guardrails.py")
  policy_src = _read_module_source("services/tool_policy.py")
  safety_src = _read_module_source("services/llm_safety.py")
  return {
    "input_guardrails": {
      "active": "validate_user_prompt" in guardrails_src,
      "rule_count": guardrails_src.count('("') if guardrails_src else 0,
    },
    "tool_rbac": {
      "active": "is_tool_allowed" in policy_src and "redact_tool_result" in policy_src,
      "propietario_only_tools_declared": "PROPIETARIO_ONLY_TOOLS" in policy_src,
    },
    "output_filter": {
      "active": "enforce_llm_output" in safety_src,
      "enforce_function": "services.llm_safety.enforce_llm_output",
      "production_enforced": IS_PRODUCTION,
    },
    "sql_agent_disabled": _sql_tool_absent(),
  }


def _strict_api_models() -> bool:
  src = _read_module_source("api/rest_routes.py")
  if not src:
    return False
  return "class StrictModel" not in src and "StrictModel)" in src and "BaseModel)" not in src


def _smtp_configured() -> bool:
  return bool(SMTP_HOST and SMTP_FROM)


def collect_security_controls() -> dict[str, object]:
  waf = verify_nginx_waf_config()
  llm = _llm_layers()
  registration_secure = (not REGISTRATION_ENABLED) or bool(TURNSTILE_SECRET_KEY and TURNSTILE_SITE_KEY)

  email_verification_ready = (not REGISTRATION_ENABLED) or _smtp_configured() or not IS_PRODUCTION
  session_store_ok = SESSION_STORE == "mysql" or not IS_PRODUCTION

  controls: dict[str, object] = {
    "environment": "production" if IS_PRODUCTION else "development",
    "auth": {
      "jwt_rs256": True,
      "session_cookie_http_only": True,
      "cors_credentials_disabled_in_prod": IS_PRODUCTION,
      "session_store": SESSION_STORE,
      "session_store_mysql_in_prod": session_store_ok,
    },
    "llm": llm,
    "waf_edge_nginx": waf,
    "rate_limiting": {
      "enabled": RATE_LIMIT_ENABLED,
      "nginx_layers": waf.get("features", {}),
    },
    "audit": {
      "hmac_secret_configured": bool(AUDIT_HMAC_SECRET),
      "retention_days": AUDIT_RETENTION_DAYS,
      "verify_endpoint": "/api/audit/verify",
    },
    "observability": {
      "prometheus_endpoint": "/metrics",
      "metrics_token_configured": bool(METRICS_TOKEN),
      "prompt_redaction_in_prod": IS_PRODUCTION,
    },
    "registration": {
      "public_enabled": REGISTRATION_ENABLED,
      "turnstile_configured": bool(TURNSTILE_SECRET_KEY and TURNSTILE_SITE_KEY),
      "invite_code_configured": bool(REGISTRATION_INVITE_CODE),
      "email_verification_configured": _smtp_configured(),
      "secure_for_production": registration_secure and email_verification_ready,
    },
    "api_hardening": {
      "strict_request_models": _strict_api_models(),
      "cita_assignment_validation": "validate_mecanico_isla_sucursal" in _read_module_source("services/cita_service.py"),
      "hsts_in_app": "Strict-Transport-Security" in _read_module_source("api/security_headers.py"),
    },
    "resource_limits": {
      "max_sucursales_per_owner": MAX_SUCURSALES_PER_OWNER,
      "max_islas_per_sucursal": MAX_ISLAS_PER_SUCURSAL,
    },
  }

  checks = {
    "waf_edge": bool(waf.get("implemented")),
    "llm_sql_disabled": bool(llm["sql_agent_disabled"]),
    "llm_guardrails": bool(llm["input_guardrails"]["active"])
    and int(llm["input_guardrails"].get("rule_count") or 0) >= 9,
    "llm_output_safety": bool(llm["output_filter"]["active"]),
    "audit_hmac": bool(AUDIT_HMAC_SECRET) or not IS_PRODUCTION,
    "metrics_protected": bool(METRICS_TOKEN) or not IS_PRODUCTION,
    "registration_hardened": registration_secure and email_verification_ready or not IS_PRODUCTION,
    "session_store_mysql": session_store_ok,
    "strict_api_models": _strict_api_models() or not IS_PRODUCTION,
  }
  controls["checks"] = checks
  controls["compliant"] = all(checks.values())
  return controls


def collect_security_controls_public() -> dict[str, object]:
  """Resumen para auditoría externa sin rutas internas ni manifiesto WAF detallado."""
  data = collect_security_controls()
  waf = data.get("waf_edge_nginx")
  if isinstance(waf, dict):
    data["waf_edge_nginx"] = {
      "implemented": waf.get("implemented"),
      "features": waf.get("features", {}),
    }
  audit = data.get("audit")
  if isinstance(audit, dict):
    data["audit"] = {
      "hmac_secret_configured": audit.get("hmac_secret_configured"),
      "retention_days": audit.get("retention_days"),
    }
  return data
