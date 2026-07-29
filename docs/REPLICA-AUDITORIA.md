# Réplica — Auditoría de seguridad (28 jul 2026)

**Target:** `https://200-234-226-167.sslip.io`  
**Informe externo:** calificación 20/100 (crítico)  
**Estado tras remediación:** ver `pentest-reports/` y `./scripts/pentest-master.sh`

---

## Resumen ejecutivo

Varios hallazgos críticos del informe corresponden a **datos de prueba persistidos** durante el pentest o a **falsos positivos** (texto guardado en BD ≠ ejecución de XSS/SSTI/SQLi). El código actual incluye validación server-side, limpieza forense automática y controles verificables.

| Hallazgo | Veredicto | Evidencia |
|----------|-----------|-----------|
| C-01 XSS inventario | **Remediado** | `iespro_taller/api/input_validation.py` + tests |
| C-02 SSTI servicios | **Falso positivo + mitigado** | Sin motor de plantillas; patrones `{{` rechazados |
| C-03 SQLi almacenado | **Falso positivo + mitigado** | Queries con `%s`; patrones SQL rechazados |
| C-04 Mass assignment | **Mitigado** | `StrictModel`, PATCH con roles y validación |
| C-05 LLM verboso | **Mitigado** | Sin `tool_calls` en prod; prompts acortados; scope sucursal |
| H-01 permissions en `/me` | **Remediado** | Prod devuelve `profile` + `ui` |
| H-02 Turnstile site key | **Remediado** | Key solo en build Vite; `captcha_configured` en API |
| H-05 Sin rate limit | **Falso** | `@rate_limit` en auth y CRUD |

---

## Pruebas de verificación

### 1. Despliegue y limpieza

```bash
cd ~/taller-ollama && git pull && ./scripts/post-deploy-prod.sh
```

Debe mostrar: `15 OK, 0 fallos` y sin residuos XSS/SSTI en BD.

### 2. XSS rechazado (con sesión)

```bash
curl -s -b cookies.txt -o /dev/null -w "%{http_code}" \
  -X POST https://200-234-226-167.sslip.io/api/inventario \
  -H "Content-Type: application/json" \
  -d '{"nombre":"<script>alert(1)</script>","cantidad":1,"precio_unitario":10}'
```

Esperado: **400** (no `200`).

### 3. SSTI rechazado

```bash
curl -s -b cookies.txt -o /dev/null -w "%{http_code}" \
  -X POST https://200-234-226-167.sslip.io/api/servicios \
  -H "Content-Type: application/json" \
  -d '{"nombre":"{{7*7}}","precio":1}'
```

Esperado: **400**.

### 4. Pentest automatizado

```bash
URL=https://200-234-226-167.sslip.io EMAIL=... PASS='...' ./scripts/pentest-master.sh
```

### 5. Postura en código

```bash
curl -s https://200-234-226-167.sslip.io/api/security/controls | jq .compliant
```

---

## Archivos clave de remediación

| Archivo | Función |
|---------|---------|
| `iespro_taller/api/input_validation.py` | Anti-XSS/SSTI/SQLi en CRUD |
| `scripts/cleanup-pentest-data.sql` | Limpieza forense post-pentest |
| `scripts/pentest-master.sh` | Pruebas de regresión |
| `iespro_taller/api/chat_response.py` | Oculta `tool_calls` en prod |
| `iespro_taller/services/tool_policy.py` | RBAC de tools IA |
| `.github/workflows/security.yml` | CI: tests + bandit + pip-audit |

---

## Mejoras conscientemente no aplicadas

| Recomendación del informe | Motivo |
|---------------------------|--------|
| Verificación de email | SMTP bloqueado en VPS |
| Invite code obligatorio | Rompía arranque; registro con Turnstile es suficiente para demo |
| Cloudflare WAF / proxy | Fuera de alcance del taller; nginx edge ya filtra rutas sensibles |

---

*Documento para entrega académica — ambiente controlado y autorizado.*
