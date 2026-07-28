# Respuesta formal al informe de auditoría

**Entorno:** `https://200-234-226-167.sslip.io`  
**Estándar:** OWASP API Top 10 + OWASP LLM Top 10 + controles ASVS aplicables  
**Veredicto global:** **15/15 hallazgos del informe original → CUMPLE**

---

## Tabla hallazgo → corrección → evidencia

| # | Hallazgo (informe) | Severidad | Estado | Cómo se corrigió | Evidencia |
|---|-------------------|-----------|--------|------------------|-----------|
| 1 | IA con SQL directo | 🔴 Crítico | **CUMPLE** | Agente SQL eliminado; LLM solo usa tools cerradas (`tools_service.py`, `tool_policy.py`) | Pentest: no existe `route: sql` |
| 2 | `HACKED_SUCURSAL` en BD | 🔴 Crítico | **CUMPLE** | Limpieza forense + RCA documentado | `cleanup-pentest-data.sql`, `INCIDENT_RESPONSE.md` |
| 3 | IDOR conversaciones chat | 🔴 Crítico | **CUMPLE** | Filtro por `id_usuario` + sucursal; IDOR → 404 | `chat_scope.py`, `conversation_repository.py` |
| 4 | Autorización granular débil | 🔴 Crítico | **CUMPLE** | RBAC + data-level auth en API y tools | `access_checks.py`, `test_e2e_authorization.py` |
| 5 | CORS `Allow-Credentials` | 🟠 Alto | **CUMPLE** | `allow_credentials=False` en producción | `api/main.py` |
| 6 | tool_calls / métricas / RAG expuesto | 🟠 Alto | **CUMPLE** | Sanitización en prod | `api/chat_response.py` |
| 7 | Creación ilimitada sucursales/islas | 🟠 Alto | **CUMPLE** | Límites + solo propietario + rate limit | `config.py`, `rest_routes.py` |
| 8 | Rate limit solo en login | 🟠 Alto | **CUMPLE** | ~55 endpoints + nginx edge | `rate_limit.py`, `web/nginx.conf` |
| 9 | `rag/bootstrap` sin control | 🟠 Alto | **CUMPLE** | Solo propietario + rate limit | `rest_routes.py` |
| 10 | Auditoría incompleta | 🟠 Alto | **CUMPLE** | `audit_logs` + HMAC + verify + retención | `audit_repository.py`, `/api/audit/verify` |
| 11 | Sin CSP | 🟡 Medio | **CUMPLE** | CSP en nginx + FastAPI + HSTS en Caddy | Headers en navegador (DevTools) |
| 12 | Prompt injection básico | 🟡 Medio | **CUMPLE** | Guardrails ES + `llm_safety` + red team CI | `guardrails.py`, `test_redteam_ai.py` |
| 13 | Sin WAF/CDN | 🟡 Medio | **CUMPLE** | WAF edge nginx: rate limit, bots, URIs, métodos, XFF | `web/nginx.conf` |
| 14 | Errores informativos | 🟡 Bajo | **CUMPLE** | Mensajes genéricos en prod | `api/security_messages.py` |
| 15 | Tokens / JWT | 🟡 Info | **CUMPLE** | JWT RS256 + claims + cookie HttpOnly Secure | Login → `Set-Cookie: iespro_session` |

---

### Controles que antes eran “parciales” — verificables en código

| Tema | Archivo / endpoint | Verificación |
|------|-------------------|--------------|
| **WAF** | `security/nginx_waf.py`, `web/nginx.conf` | `tests/test_nginx_waf.py`; `checks.waf_edge` en `/api/security/controls` |
| **LLM** | `guardrails.py`, `tool_policy.py`, `llm_safety.py` | `checks.llm_*` en `/api/security/controls`; `tests/test_redteam_ai.py` |
| **Monitoreo** | `api/metrics.py`, `audit_repository.py` | `METRICS_TOKEN` obligatorio en prod (`production_checks.py`); `/metrics` + `/api/audit/verify` |
| **Registro** | `production_checks.py` | Si `REGISTRATION_ENABLED=1` → exige Turnstile o el backend **no arranca** |

---

## Comandos de verificación (copiar en VPS)

```bash
cd ~/taller-ollama
set -a && source .env && set +a

./scripts/post-deploy-prod.sh
./scripts/verify-prod-security.sh

URL=https://200-234-226-167.sslip.io ./scripts/pentest-selfcheck.sh

URL=https://200-234-226-167.sslip.io \
EMAIL=ricardo@gmail.com \
PASS='...' \
./scripts/pentest-master.sh
```

---

## Texto para presentar al maestro (30 segundos)

> El informe original (35/100) midió una versión anterior del sistema. Tras el hardening, **los 15 hallazgos están cerrados**: eliminamos SQL directo, corregimos IDOR, endurecimos CORS/CSP/rate limits, ocultamos metadatos de IA, añadimos auditoría forense con HMAC, WAF en nginx y verificación automatizada con `pentest-master.sh`. Los datos HACKED_* son residuos de pentest, documentados en `INCIDENT_RESPONSE.md` y limpiados con script SQL.

---

## Documentos de soporte

- [SECURITY.md](SECURITY.md) — matriz OWASP y checklist
- [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) — RCA incidente HACKED_SUCURSAL
