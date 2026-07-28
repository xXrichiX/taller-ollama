# Respuesta al incidente HACKED_SUCURSAL (pentest julio 2026)

Plantilla para documentar remediación. Completa cada sección y guarda una copia en `pentest-reports/`.

---

## Resumen

| Campo | Valor |
|-------|-------|
| **Incidente** | Residuos de pentest (`HACKED_SUCURSAL`, conversaciones 11/12) |
| **Severidad** | Crítico (datos de prueba visibles en auditoría) |
| **Estado** | ☐ Abierto / ☐ En remediación / ☐ Cerrado |
| **Entorno** | `https://________________` |
| **Responsable** | ________________ |
| **Fecha cierre** | ________________ |

---

## Cronología

1. **Detección:** Informe de auditoría externa (nota 35/100) — agente SQL, IDOR conversaciones, datos `HACKED_*`.
2. **Contención:** Despliegue de código corregido (`develop`): sin SQL directo, IDOR fix, CSP, JWT RS256.
3. **Erradicación:** Ejecutar `scripts/cleanup-pentest-data.sql` en MySQL de producción.
4. **Recuperación:** Rotar secretos si hubo exposición real (no solo pentest controlado).
5. **Verificación:** `./scripts/pentest-master.sh` en verde + `./scripts/forensics-post-incident.sh`.

---

## Evidencia pre-remediación

```bash
# Consultas ejecutadas (pegar salida o adjuntar informe forensics-*.md)
SELECT id, nombre, activo FROM sucursales WHERE nombre LIKE '%HACKED%';
SELECT COUNT(*) FROM conversaciones WHERE id IN (11, 12);
```

**Resultado:** _______________________________________________

---

## Acciones de remediación

- [ ] `git pull` + `docker compose -f docker-compose.prod.yml up -d --build`
- [ ] `./scripts/post-deploy-prod.sh` (cleanup + verificación)
- [ ] Rotar `MYSQL_ROOT_PASSWORD` y `MYSQL_APP_PASSWORD` (si aplica)
- [ ] Regenerar claves JWT (`iespro_taller/data/keys/` o `JWT_*_PEM`)
- [ ] Reiniciar backend para invalidar sesiones
- [ ] Pentest verde: `URL=... EMAIL=... PASS=... ./scripts/pentest-master.sh`

---

## Evidencia post-remediación

| Verificación | Resultado |
|--------------|-----------|
| Sin `HACKED_SUCURSAL` activa | ☐ OK |
| IDOR conversaciones (404 ajeno) | ☐ OK |
| Sin `route: sql` en chat | ☐ OK |
| `APP_ENV=production` en backend | ☐ OK |
| Pentest ≥ 85/100 | ☐ OK |

**Salida pentest (resumen):** _______________________________________________

**Informe forense:** `pentest-reports/forensics-________.md`

---

## Causa raíz

☐ Pentest controlado (datos de prueba no eliminados tras auditoría)  
☐ Compromiso real (especificar vector)  
☐ Configuración incorrecta en despliegue  

**Notas:** El código actual no permite crear `HACKED_SUCURSAL` vía API sin permisos; los registros provienen de pruebas manuales o versión anterior del agente.

---

## Lecciones aprendidas

1. Ejecutar cleanup SQL tras cada pentest en entornos compartidos.
2. Automatizar verificación con `post-deploy-prod.sh` + CI.
3. Mantener `audit_logs` para acciones sensibles (citas, usuarios, RAG).

---

## Aprobación de cierre

| Rol | Nombre | Fecha |
|-----|--------|-------|
| Desarrollo | | |
| Operaciones | | |
