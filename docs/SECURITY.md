# Seguridad IESPRO-Taller — OWASP / ASVS

## Arquitectura IA (Prioridad 1)

El LLM **no ejecuta SQL**. Solo invoca tools del catálogo cerrado (`tools_service.py`), que llaman servicios internos con validación de rol y sucursal.

```
Usuario → Chat API → LLM → Tools (RBAC) → Servicios → MySQL
```

## Controles implementados

| Área | Control |
|------|---------|
| Auth | JWT RS256 (`api/jwt_tokens.py`), cookie HttpOnly, idle timeout |
| RBAC | Tools por rol, endpoints con `_require_propietario`, `access_checks` |
| Data-level | Filtros por sucursal/cliente/mecánico en API y servicios |
| IA output | `public_chat_result`, `output_filter`, `llm_safety` (bloqueo PII/SQL), stream validado en prod |
| RAG | `hybrid_search` sin fallback global si el filtro vacía resultados |
| Auditoría | `audit_logs` + login/logout/cambios críticos |
| Rate limit | IP real detrás de proxy, límites en auth/chat/CRUD + nginx edge |
| WAF edge | nginx: `limit_req`, bloqueo User-Agent/URI de escaneo, 404 rutas sensibles |
| Errores API | Mensajes genéricos en prod (`api/security_messages.py`) — anti-enumeración |
| CSP / HSTS | nginx + FastAPI + Caddy redirect HTTPS |
| Secretos | `.env` gitignored; prod exige contraseñas ≥16 chars y claves JWT |
| CI | pip-audit, npm audit, bandit, tests de seguridad |

## Checklist producción

1. `MYSQL_APP_PASSWORD` y `MYSQL_ROOT_PASSWORD` aleatorios ≥16 caracteres
2. Claves JWT en `JWT_PRIVATE_KEY_PEM` / `JWT_PUBLIC_KEY_PEM` o volumen `data/keys/`
3. `REGISTRATION_ENABLED=0` o invite + Turnstile
4. `TRUST_PROXY_HEADERS=1` detrás de Caddy
5. `./scripts/setup-prod-env.sh` y `./scripts/post-deploy-prod.sh` tras deploy
6. Backup diario: `./scripts/backup-mysql.sh`
7. WAF edge nginx (rate limit + bloqueo bots); Cloudflare opcional delante del VPS
8. Secretos en Vault/Key Vault para equipos enterprise

## Respuesta a incidentes

1. Aislar el servicio afectado y revisar `audit_logs` y logs de Caddy
2. Rotar contraseñas MySQL, claves JWT y reiniciar backend
3. Restaurar desde backup si hubo compromiso de datos: `./scripts/backup-mysql.sh`

## Monitoreo (Prioridad 19 — roadmap)

Integrar Prometheus/Grafana/OpenTelemetry en el VPS. Mientras tanto: logs de `audit_logs`, `llm_observability_logs` y Caddy access logs.

## OWASP mapping

- **API1 Broken Object Level Authorization** → `access_checks`, `chat_scope`, conversaciones por usuario
- **API2 Broken Authentication** → JWT RS256, bcrypt, rate limit login
- **API3 Broken Object Property Level Authorization** → redacción PII en tools
- **API4 Unrestricted Resource Consumption** → rate limits, MAX_TOOL_CALLS_PER_TURN
- **API5 Broken Function Level Authorization** → RBAC endpoints + tools
- **LLM01 Prompt Injection** → guardrails + sanitize context
- **LLM02 Insecure Output** → `output_filter` + `llm_safety.enforce_llm_output` (bloqueo en prod)
- **LLM06 Sensitive Information Disclosure** → redact_tool_result, prod sin tool_calls
