# Seguridad IESPRO-Taller — OWASP / ASVS

## Arquitectura IA (Prioridad 1)

El LLM **no ejecuta SQL**. Solo invoca tools del catálogo cerrado (`tools_service.py`), que llaman servicios internos con validación de rol y sucursal.

```
Usuario → Chat API → LLM → Tools (RBAC) → Servicios → MySQL
```

## Controles implementados

| Área | Control |
|------|---------|
| Auth | JWT RS256 con claims `sub`, `rol`, `sucursal`, `jti`; cookie HttpOnly; idle timeout; reemisión al cambiar sucursal |
| RBAC | Tools por rol, endpoints con `_require_propietario`, `access_checks`, `require_catalog_reader` |
| Data-level | Filtros por sucursal/cliente/mecánico en API y servicios; conversaciones por usuario+sucursal |
| IA output | `public_chat_result`, `output_filter`, `llm_safety` (bloqueo PII/SQL), stream validado en prod |
| RAG | `hybrid_search` sin fallback global; bootstrap solo propietario + rate limit |
| Auditoría | `audit_logs` + middleware `api.access` en cada petición autenticada + cambios críticos |
| Rate limit | slowapi en todos los endpoints + default 120/min + nginx edge por ruta |
| WAF edge | nginx: `limit_req`, `limit_conn`, bloqueo UA/URI/métodos, 404 rutas sensibles |
| Errores API | Mensajes genéricos en prod (400/404/503) vía `security_messages.py` |
| CSP / HSTS | CSP en nginx + FastAPI (siempre) + Caddy redirect HTTPS |
| Incidentes | `ensure_deactivate_compromised_sucursales()` al arrancar (nombres HACKED/backdoor/etc.) |
| Secretos | `.env` gitignored; prod exige contraseñas ≥16 chars y claves JWT |
| CI | pip-audit, npm audit, bandit, tests de seguridad |

## Checklist producción

1. `MYSQL_APP_PASSWORD` y `MYSQL_ROOT_PASSWORD` aleatorios ≥16 caracteres
2. Claves JWT en `JWT_PRIVATE_KEY_PEM` / `JWT_PUBLIC_KEY_PEM` o volumen `data/keys/`
3. `REGISTRATION_ENABLED=0` o invite + Turnstile
4. `TRUST_PROXY_HEADERS=1` detrás de Caddy
5. `APP_ENV=production`
6. `./scripts/setup-prod-env.sh` y `./scripts/post-deploy-prod.sh` tras deploy
7. Backup diario: `./scripts/backup-mysql.sh`
8. WAF edge nginx; Cloudflare opcional delante del VPS
9. Revisar `audit_logs` tras deploy (buscar `security.compromised_sucursal`)

## Respuesta a incidentes

1. Aislar el servicio afectado y revisar `audit_logs` y logs de Caddy
2. Rotar contraseñas MySQL, claves JWT y reiniciar backend
3. Restaurar desde backup si hubo compromiso de datos: `./scripts/backup-mysql.sh`
4. Verificar que `ensure_deactivate_compromised_sucursales` desactivó artefactos sospechosos

## Monitoreo (Prioridad 19 — roadmap)

Integrar Prometheus/Grafana/OpenTelemetry en el VPS. Mientras tanto: logs de `audit_logs`, `llm_observability_logs` y Caddy access logs.

## OWASP mapping

- **API1 Broken Object Level Authorization** → `access_checks`, `chat_scope`, conversaciones por usuario
- **API2 Broken Authentication** → JWT RS256, bcrypt, rate limit login
- **API3 Broken Object Property Level Authorization** → redacción PII en tools
- **API4 Unrestricted Resource Consumption** → rate limits en todos los endpoints, MAX_TOOL_CALLS_PER_TURN
- **API5 Broken Function Level Authorization** → RBAC endpoints + tools + `require_catalog_reader`
- **LLM01 Prompt Injection** → guardrails ampliados + sanitize context
- **LLM02 Insecure Output** → `output_filter` + `llm_safety.enforce_llm_output` (bloqueo en prod)
- **LLM06 Sensitive Information Disclosure** → redact_tool_result, prod sin tool_calls
