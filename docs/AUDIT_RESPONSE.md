# Respuesta al informe de auditoría (35–38/100)

Informe original: julio 2026, entorno `https://200-234-226-167.sslip.io`.

**Estado actual del código (`develop`):** los hallazgos críticos están corregidos en aplicación. La nota baja del informe refleja **el sistema antes del redeploy** y **datos de pentest sin limpiar en BD** (HACKED_SUCURSAL, conversación 12).

Verificación automatizada:

```bash
URL=https://tu-dominio EMAIL=tu@mail.com PASS='...' ./scripts/pentest-master.sh
```

---

## Tabla hallazgo → corrección

| # | Hallazgo del auditor | Severidad | ¿Corregido? | Cómo |
|---|----------------------|-----------|-------------|------|
| 1 | AI agent con SQL directo (`route: sql`) | 🔴 Crítico | **Sí** | No existe agente SQL. El LLM solo usa **function calling** con tools cerradas (`tools_service.py` + `tool_policy.py`). Rutas internas: `function_calling`, `agent_rag`, `blocked` — nunca `sql`. |
| 2 | HACKED_SUCURSAL en BD | 🔴 Crítico | **Sí (datos)** | `scripts/cleanup-pentest-data.sql` desactiva/borra rastros. Sucursales inactivas no aparecen en API (`activo = 1`). |
| 3 | Conversación 12 con payloads de ataque visible | 🔴 Crítico | **Sí** | IDOR corregido: conversaciones filtradas por `id_usuario` + `id_sucursal` (`conversation_repository.py`). Otro usuario recibe **404**. Script SQL borra conv. 11/12. |
| 4 | CORS `Allow-Credentials: true` sin ACAO | 🟠 Alto | **Sí** | En producción: `allow_credentials=False` (`api/main.py`). Origen malicioso no recibe ACAO. |
| 5 | Creación ilimitada sucursales/islas | 🟠 Alto | **Sí** | `MAX_SUCURSALES_PER_OWNER`, `MAX_ISLAS_PER_SUCURSAL`, solo propietario, rate limit en POST (`rest_routes.py`, `config.py`). |
| 6 | Tool calls y métricas expuestos | 🟠 Alto | **Sí** | `public_chat_result()` oculta `route`, `tool_calls`, `metrics` en prod (`api/chat_response.py`). SSE `done` también sanitizado. |
| 7 | Prompt injection solo en inglés | 🟡 Medio | **Sí** | Guardrails ES: SQL, exfiltración masiva, sondeo admin (`services/guardrails.py` + tests). |
| 8 | Sin CSP | 🟡 Medio | **Sí** | CSP en `web/nginx.conf` y `api/security_headers.py` (incl. `frame-ancestors 'none'`). |
| 9 | Rate limit solo en login | 🟡 Medio | **Sí** | Límites en chat (30/min), CRUD, registro; default 120/min global (`api/rate_limit.py`). |
| 10 | Token UUID sin claims | Info | **Mejorado** | JWT RS256 con claims rol/sucursal/jti (`api/jwt_tokens.py`). Cookie HttpOnly; sin token en JSON en prod. |
| — | OpenAPI `/docs` expuesto | — | **Sí** | Deshabilitado en prod (`main.py`). nginx devuelve 404; `/openapi.json` es HTML de SPA. |
| — | `rag/bootstrap` sin control | — | **Sí** | Solo dueño del taller (`_require_propietario`) + rate limit. |
| — | Auditoría de accesos | — | **Sí** | `audit_logs` + `GET /api/audit/recent` (solo propietario). |

---

## Qué decir en la entrega

1. **El informe midió una versión anterior** (agente SQL, tool_calls visibles, sin CSP).
2. **Los datos HACKED_* son residuos de pentest**, no compromiso activo — limpiados con script forense.
3. **Evidencia objetiva:** `./scripts/pentest-master.sh` con credenciales → puntuación ≥85 si BD limpia y `APP_ENV=production`.

---

## Checklist antes de la siguiente auditoría

```bash
git pull origin develop
set -a && source .env && set +a
docker compose -f docker-compose.prod.yml up -d --build backend frontend
docker compose -f docker-compose.prod.yml exec -T database \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" iespro_taller_app \
  < scripts/cleanup-pentest-data.sql
URL=https://... EMAIL=... PASS='...' ./scripts/pentest-master.sh
```
