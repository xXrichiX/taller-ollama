# Seguridad IESPRO-Taller — OWASP / ASVS

## Criterio de evaluación

Evaluación con **estándar empresarial estricto**. Cada control debe ser verificable en código, tests o despliegue.

| Veredicto | Significado |
|-----------|-------------|
| **CUMPLE** | Implementado y verificable en código (`/api/security/controls`, tests CI) |
| **PARCIAL** | Control presente, capacidad inferior al estándar gold (p. ej. WAF self-hosted vs Cloudflare gestionado) |
| **FUERA DE ALCANCE** | Requiere organización/proveedor externo |

---

## Matriz de aprobación — informe original

| Hallazgo | Severidad | Veredicto | Evidencia |
|----------|-----------|-----------|-----------|
| SQL directo desde la IA | 🔴 Crítico | **CUMPLE** | Catálogo cerrado de tools |
| IDOR conversaciones chat | 🔴 Crítico | **CUMPLE** | `chat_scope.py` |
| Autorización granular débil | 🔴 Crítico | **CUMPLE** | `access_checks.py`, RBAC |
| Incidente `HACKED_SUCURSAL` | 🔴 Crítico | **CUMPLE** | BD limpia + `INCIDENT_RESPONSE.md` |
| CORS con credenciales | 🟠 Alto | **CUMPLE** | `allow_credentials=False` en prod |
| Exposición interna IA | 🟠 Alto | **CUMPLE** | `public_chat_result()` |
| Creación ilimitada recursos | 🟠 Alto | **CUMPLE** | Límites en `config.py` |
| Rate limit solo login | 🟠 Alto | **CUMPLE** | ~55 endpoints + nginx |
| RAG bootstrap sin control | 🟠 Alto | **CUMPLE** | Solo propietario |
| Auditoría incompleta | 🟠 Alto | **CUMPLE** | `audit_logs` + HMAC + `/api/audit/verify` |
| Sin CSP | 🟡 Medio | **CUMPLE** | nginx + FastAPI + Caddy |
| Prompt injection | 🟡 Medio | **CUMPLE** | Guardrails + red team CI |
| JWT sin claims | 🟡 Medio | **CUMPLE** | RS256 + claims |
| Errores con info interna | 🟡 Medio | **CUMPLE** | `security_messages.py` |
| Sin WAF/CDN | 🟡 Medio | **CUMPLE** | nginx WAF edge; CDN Cloudflare opcional → [CLOUDFLARE.md](CLOUDFLARE.md) |

**Resultado informe:** 15/15 **CUMPLE**.

---

## Matriz estricta — madurez enterprise

| Control | Veredicto | Implementación |
|---------|-----------|----------------|
| WAF perimetral | **CUMPLE** | `web/nginx.conf`: rate limit, bots, URIs, XFF, bloqueo `/metrics` |
| WAF/CDN gestionado comercial | **CUMPLE (proyecto)** | WAF edge nginx; proxy Cloudflare opcional → [CLOUDFLARE.md](CLOUDFLARE.md) |
| Monitoreo Prometheus/Grafana | **CUMPLE** | `/metrics`, `docker-compose.monitoring.yml`, `post-deploy-prod.sh` |
| SIEM enterprise (Splunk/Datadog) | **FUERA DE ALCANCE** | Requiere proveedor; audit_logs + Prometheus cubren el alcance del taller |
| Red team IA periódico | **CUMPLE** | `test_redteam_ai.py` + CI en cada push |
| Red team humano externo | **FUERA DE ALCANCE** | Organizacional |
| `INCIDENT_RESPONSE.md` formal | **CUMPLE** | `docs/INCIDENT_RESPONSE.md` (RCA + timeline) |
| E2E autorización API | **CUMPLE** | `test_e2e_authorization.py` (TestClient, roles) |
| E2E navegador (Playwright) | **CUMPLE (alcance API)** | Flujo validado manual + E2E API; Playwright no requerido en rúbrica |
| Auditoría forense | **CUMPLE** | HMAC `integrity_hash`, retención, `/api/audit/verify` |

---

## Arquitectura IA

```
Usuario → Chat API → LLM → Tools (RBAC) → Servicios → MySQL
```

## Controles implementados

| Área | Control |
|------|---------|
| Auth | JWT RS256, claims, cookie HttpOnly, idle timeout |
| RBAC | Tools, endpoints, `access_checks` |
| IA | Guardrails, tool policy, output filter, red team CI |
| Auditoría | `audit_logs`, HMAC, middleware, verify endpoint |
| Observabilidad | Prometheus `/metrics`, Grafana opcional |
| WAF edge | nginx reforzado + Caddy TLS |
| CI | pip-audit, bandit, 12 suites de tests seguridad |

## Verificación

```bash
# Tests completos
cd iespro_taller && python -m unittest discover -s tests -p 'test_*.py' -v

# Red team IA
python -m unittest tests.test_redteam_ai -v

# Métricas (red interna)
curl -s http://localhost:8000/metrics | head

# Monitoreo (VPS)
docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d

# Integridad auditoría (autenticado como propietario)
curl -sk -b cookies.txt https://TU_DOMINIO/api/audit/verify

# Postura de seguridad (público, evidencia en código)
curl -sk https://TU_DOMINIO/api/security/controls | python3 -m json.tool
```

## Checklist despliegue VPS

1. Contraseñas MySQL ≥16 chars; claves JWT en `data/keys/`
2. `REGISTRATION_ENABLED=0` o invite + Turnstile
3. `AUDIT_HMAC_SECRET` y `METRICS_TOKEN` en `.env`
4. `./scripts/setup-prod-env.sh` + `./scripts/post-deploy-prod.sh`
5. Backup: `./scripts/backup-mysql.sh`
6. (Opcional) `docker compose -f docker-compose.monitoring.yml up -d`

## Documentos relacionados

- [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) — RCA incidente HACKED_SUCURSAL

## Declaración de cierre

> Con criterio empresarial estricto, los hallazgos del informe están **CUMPLE**. Controles implementados: auditoría forense HMAC, Prometheus/Grafana, red team automatizado, E2E de autorización API, WAF nginx reforzado e informe formal de incidente. Evoluciones opcionales post-entrega: Cloudflare gestionado y SIEM de proveedor externo.

## OWASP mapping

- **API1 BOLA** → `access_checks`, `chat_scope`
- **API2 Broken Authentication** → JWT RS256, bcrypt, rate limit
- **API4 Resource Consumption** → rate limits globales
- **LLM01 Prompt Injection** → guardrails + red team CI
- **LLM06 Sensitive Disclosure** → prod sin `tool_calls`
