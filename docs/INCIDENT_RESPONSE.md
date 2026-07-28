# Informe de respuesta al incidente — IESPRO-Taller

**ID:** INC-2026-001  
**Clasificación:** Compromiso de datos / pentest  
**Estado:** Cerrado — remediado  
**Fecha detección:** 2026 (auditoría de seguridad del proyecto)  
**Fecha cierre:** 2026-07-28  

---

## 1. Resumen ejecutivo

Durante pruebas de penetración se identificaron artefactos maliciosos en la base de datos (sucursal `HACKED_SUCURSAL`, usuarios de prueba, posible escalación vía chat IDOR y exposición de internals de la IA). Se ejecutó remediación técnica completa, rotación de credenciales, endurecimiento de la aplicación y verificación post-deploy en VPS.

---

## 2. Timeline

| Fecha | Evento |
|-------|--------|
| T0 | Informe de auditoría entregado con hallazgos críticos |
| T0+1d | Desactivación de SQL directo en IA; RBAC en tools |
| T0+2d | Corrección IDOR en conversaciones; JWT RS256 con claims |
| T0+3d | Rate limits globales; auditoría `audit_logs`; guardrails IA |
| T0+4d | Limpieza BD (0 sucursales HACKED activas); deploy VPS |
| T0+5d | Verificación: health OK, rate limit 429, Turnstile activo |
| Cierre | Controles automatizados en CI + `ensure_deactivate_compromised_sucursales` |

---

## 3. Impacto

| Área | Impacto | Estado |
|------|---------|--------|
| Confidencialidad | Riesgo de lectura de chats ajenos (IDOR) | **Mitigado** |
| Integridad | Sucursales/usuarios de pentest en BD | **Limpiado** |
| Disponibilidad | Rate limit ausente en varios endpoints | **Mitigado** |
| Datos PII | Exposición vía tools IA sin RBAC | **Mitigado** |

**Datos exfiltrados en producción real:** no confirmado tras limpieza. Entorno tratado como comprometido hasta rotación de secretos.

---

## 4. Causa raíz (RCA)

1. **Autorización insuficiente** — endpoints y chat sin scope estricto por usuario/sucursal.
2. **Superficie IA amplia** — tools con acceso amplio y salida sin filtrar en producción.
3. **Controles perimetrales incompletos** — rate limiting parcial; sin auditoría centralizada.
4. **Datos de pentest persistidos** — artefactos `HACKED_*` no purgados tras pruebas.

---

## 5. Acciones de contención

1. Desactivar sucursales con nombres sospechosos al arrancar (`init_db.ensure_deactivate_compromised_sucursales`).
2. Rotar `MYSQL_ROOT_PASSWORD`, `MYSQL_APP_PASSWORD` y claves JWT RS256.
3. Reiniciar stack Docker en VPS.
4. Revisar `audit_logs` y logs Caddy.

---

## 6. Acciones correctivas (implementadas)

| Control | Archivo / componente |
|---------|---------------------|
| Anti-IDOR chat | `api/chat_scope.py` |
| RBAC API | `api/access_checks.py` |
| RBAC tools IA | `services/tool_policy.py` |
| Guardrails prompt injection | `services/guardrails.py` |
| JWT RS256 + claims | `api/jwt_tokens.py` |
| Auditoría + HMAC integridad | `db/audit_repository.py`, `/api/audit/verify` |
| Rate limit global | `api/rest_routes.py`, `web/nginx.conf` |
| Métricas Prometheus | `api/metrics.py`, `docker-compose.monitoring.yml` |
| Red team automatizado | `tests/test_redteam_ai.py`, CI |
| E2E autorización | `tests/test_e2e_authorization.py` |

---

## 7. Verificación post-incidente

```bash
# 0 sucursales comprometidas activas
SELECT COUNT(*) FROM sucursales WHERE activo=1 AND nombre REGEXP 'hacked|backdoor|pwned';

# Health
curl -sk https://TU_DOMINIO/api/health

# Integridad auditoría (como propietario autenticado)
curl -sk -b cookies.txt https://TU_DOMINIO/api/audit/verify
```

---

## 8. Lecciones aprendidas

1. Toda prueba de pentest debe usar datos desechables y script de limpieza.
2. La IA requiere el mismo RBAC que la API REST.
3. `audit_logs` con HMAC permite detectar alteración posterior.
4. CI debe incluir red team automatizado de prompts adversariales.

---

## 9. Comunicación

| Audiencia | Mensaje |
|-----------|---------|
| Equipo de desarrollo | Remediación completada; ver `docs/SECURITY.md` |
| Evaluador académico | Hallazgos críticos cerrados con evidencia en VPS |
| Usuarios finales | No aplica (entorno demo académico) |

---

## 10. Aprobación de cierre

| Rol | Nombre | Fecha | Firma |
|-----|--------|-------|-------|
| Responsable técnico | Ricardo | 2026-07-28 | Cerrado |

**Próxima revisión:** anual o tras nuevo pentest.
