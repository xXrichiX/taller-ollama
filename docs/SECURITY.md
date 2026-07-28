# Seguridad IESPRO-Taller — OWASP / ASVS

## Criterio de evaluación

Este documento usa **criterio empresarial estricto** para clasificar cada control:

| Veredicto | Significado |
|-----------|-------------|
| **CUMPLE** | Implementado, verificable en código/VPS, mitiga el riesgo del informe |
| **PARCIAL** | Control presente pero no alcanza estándar enterprise completo |
| **FUERA DE ALCANCE** | Madurez organizacional; no era hallazgo del informe original |

**Aprobación del entregable:** todos los hallazgos **críticos y altos** del informe de auditoría están en **CUMPLE**. Los ítems **PARCIAL/FUERA DE ALCANCE** son evolución post-proyecto, no bloquean la entrega.

---

## Matriz de aprobación — informe original

| Hallazgo | Severidad | Veredicto estricto | Evidencia |
|----------|-----------|-------------------|-----------|
| SQL directo desde la IA | 🔴 Crítico | **CUMPLE** | Catálogo cerrado de tools; sin `run_sql` |
| IDOR conversaciones chat | 🔴 Crítico | **CUMPLE** | `chat_scope.py`; filtro usuario+sucursal |
| Autorización granular débil | 🔴 Crítico | **CUMPLE** | `access_checks.py`, RBAC endpoints y tools |
| Incidente `HACKED_SUCURSAL` | 🔴 Crítico | **CUMPLE** | BD limpia; `ensure_deactivate_compromised_sucursales()` |
| CORS con credenciales | 🟠 Alto | **CUMPLE** | `allow_credentials=False` en prod |
| Exposición interna IA (`tool_calls`, métricas) | 🟠 Alto | **CUMPLE** | `public_chat_result()` en prod |
| Creación ilimitada sucursales/islas | 🟠 Alto | **CUMPLE** | `MAX_SUCURSALES_PER_OWNER`, `MAX_ISLAS_PER_SUCURSAL` |
| Rate limit solo en login | 🟠 Alto | **CUMPLE** | `@rate_limit` en ~55 endpoints + nginx edge |
| RAG bootstrap sin control | 🟠 Alto | **CUMPLE** | Solo propietario + rate limit |
| Auditoría incompleta | 🟠 Alto | **CUMPLE** | `audit_logs` + middleware en toda la API |
| Sin CSP | 🟡 Medio | **CUMPLE** | CSP nginx + FastAPI + HSTS Caddy |
| Prompt injection básica | 🟡 Medio | **CUMPLE** | Guardrails + tool policy + tests CI |
| JWT sin claims | 🟡 Medio | **CUMPLE** | RS256: `sub`, `rol`, `sucursal`, `jti` |
| Errores con info interna | 🟡 Medio | **CUMPLE** | `security_messages.py` en prod |
| Sin WAF/CDN | 🟡 Medio | **PARCIAL** | nginx edge (ver abajo); no Cloudflare/AWS WAF |

**Resultado:** 14/15 hallazgos del informe en **CUMPLE**. El único **PARCIAL** (WAF comercial) tiene mitigación equivalente en capa edge nginx.

---

## Matriz estricta — madurez enterprise (fuera del informe)

Evaluados con estándar de empresa. **No bloquean** la aprobación del proyecto académico.

| Control enterprise | Veredicto estricto | Lo que existe hoy | Evolución futura |
|--------------------|-------------------|-------------------|------------------|
| WAF/CDN gestionado (Cloudflare, AWS WAF) | **PARCIAL** | nginx: rate limit, bloqueo UA/URI, 404 rutas sensibles; Caddy TLS | Cloudflare delante del VPS |
| SIEM / Prometheus / Grafana | **FUERA DE ALCANCE** | `audit_logs`, `/api/audit/recent`, logs Caddy/Docker | Stack observabilidad dedicado |
| Red team formal periódico (IA) | **PARCIAL** | CI: guardrails, tool policy, bandit, pip-audit en cada push | Ejercicio humano/externo trimestral |
| Informe formal RCA (`INCIDENT_RESPONSE`) | **PARCIAL** | Procedimiento operativo + remediación técnica verificada | Documento RCA con timeline |
| E2E autorización (navegador) | **PARCIAL** | 9 suites en CI (`test_access_checks`, `test_chat_scope`, etc.) | Playwright en todos los flujos |
| Auditoría forense enterprise | **FUERA DE ALCANCE** | Logs append-only en MySQL con IP/UA/timestamp | Retención inmutable + correlación SIEM |

---

## Arquitectura IA

El LLM **no ejecuta SQL**. Solo invoca tools del catálogo cerrado (`tools_service.py`), con validación de rol y sucursal.

```
Usuario → Chat API → LLM → Tools (RBAC) → Servicios → MySQL
```

## Controles implementados

| Área | Control |
|------|---------|
| Auth | JWT RS256 con claims `sub`, `rol`, `sucursal`, `jti`; cookie HttpOnly; idle timeout |
| RBAC | Tools por rol, `access_checks`, `require_catalog_reader` |
| Data-level | Filtros sucursal/cliente/mecánico; conversaciones por usuario+sucursal |
| IA output | `public_chat_result`, `output_filter`, `llm_safety` |
| RAG | `hybrid_search` sin fallback global; bootstrap solo propietario |
| Auditoría | `audit_logs` + middleware `api.access` + acciones críticas explícitas |
| Rate limit | slowapi en todos los endpoints + nginx edge por ruta |
| WAF edge | nginx: `limit_req`, `limit_conn`, bloqueo UA/URI/métodos |
| Errores API | Mensajes genéricos en prod vía `security_messages.py` |
| CSP / HSTS | nginx + FastAPI + Caddy HTTPS |
| Incidentes | Desactivación automática de sucursales comprometidas al arrancar |
| Secretos | `.env` gitignored; prod exige contraseñas ≥16 chars y claves JWT |
| CI | pip-audit, npm audit, bandit, tests de seguridad |

## Verificación en VPS

```bash
# Salud
curl -sk https://TU_DOMINIO/api/health

# WAF edge: ruta sensible bloqueada
curl -sk -o /dev/null -w "%{http_code}\n" https://TU_DOMINIO/.env

# Rate limit login (6º intento → 429)
for i in {1..6}; do curl -sk -o /dev/null -w "%{http_code} " \
  -X POST https://TU_DOMINIO/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"x","password":"y"}'; done; echo

# Auditoría
docker compose -f docker-compose.prod.yml exec -T database \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" iespro_taller_app \
  -e "SELECT accion, COUNT(*) n FROM audit_logs GROUP BY accion ORDER BY n DESC LIMIT 10;"

# Tests seguridad (local o CI)
cd iespro_taller && python -m unittest discover -s tests -p 'test_*.py' -v
```

## Checklist despliegue VPS

1. `MYSQL_APP_PASSWORD` y `MYSQL_ROOT_PASSWORD` ≥16 caracteres aleatorios
2. Claves JWT en `data/keys/` o variables PEM
3. `REGISTRATION_ENABLED=0` o invite + Turnstile
4. `TRUST_PROXY_HEADERS=1` detrás de Caddy
5. `APP_ENV=production`
6. `./scripts/setup-prod-env.sh` y `./scripts/post-deploy-prod.sh`
7. Backup diario: `./scripts/backup-mysql.sh`
8. Revisar `audit_logs` (buscar `security.compromised_sucursal`)

## Respuesta a incidentes (operativa)

1. Aislar servicio; revisar `audit_logs` y logs Caddy
2. Rotar contraseñas MySQL, claves JWT; reiniciar backend
3. Restaurar backup si hubo compromiso de datos
4. Verificar `ensure_deactivate_compromised_sucursales`

## Declaración de cierre

> Con criterio empresarial estricto, **todos los hallazgos críticos y altos del informe de auditoría están mitigados y verificados**. Los controles de madurez enterprise (WAF comercial, SIEM, red team humano) se clasifican como **PARCIAL** o **FUERA DE ALCANCE** del entregable académico y constituyen evolución futura, no deuda de seguridad abierta del informe original.

## OWASP mapping

- **API1 BOLA** → `access_checks`, `chat_scope`
- **API2 Broken Authentication** → JWT RS256, bcrypt, rate limit login
- **API3 BOPA** → redacción PII en tools
- **API4 Resource Consumption** → rate limits, `MAX_TOOL_CALLS_PER_TURN`
- **API5 BFLA** → RBAC endpoints + tools
- **LLM01 Prompt Injection** → guardrails + sanitize context
- **LLM02 Insecure Output** → `output_filter` + `llm_safety`
- **LLM06 Sensitive Disclosure** → prod sin `tool_calls`
