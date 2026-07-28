#!/usr/bin/env bash
# Verificación rápida post-despliegue: health, headers, WAF edge, auditoría, monitoring.
# Uso: cd ~/taller-ollama && ./scripts/verify-prod-security.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

URL="${URL:-https://200-234-226-167.sslip.io}"
URL="${URL%/}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

PASS=0
FAIL=0

ok()   { echo "  ✅ $*"; PASS=$((PASS + 1)); }
bad()  { echo "  ❌ $*"; FAIL=$((FAIL + 1)); }
warn() { echo "  ⚠️  $*"; }

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "==> Verificación de seguridad — $URL"
echo ""

echo "1. Health API"
body="$(curl -sk "$URL/api/health" 2>/dev/null || true)"
if echo "$body" | grep -q '"status":"ok"'; then
  ok "GET /api/health → ok"
else
  bad "GET /api/health falló: $body"
fi

echo ""
echo "2. Headers de hardening (HTTPS)"
headers="$(curl -skI "$URL/" 2>/dev/null || true)"
echo "$headers" | grep -qi 'content-security-policy' && ok "CSP presente" || bad "Sin CSP"
echo "$headers" | grep -qi 'strict-transport-security' && ok "HSTS presente" || bad "Sin HSTS"
echo "$headers" | grep -qi 'x-frame-options: deny' && ok "X-Frame-Options DENY" || bad "Sin X-Frame-Options"
echo "$headers" | grep -qi 'x-content-type-options: nosniff' && ok "X-Content-Type-Options" || bad "Sin nosniff"

echo ""
echo "3. WAF edge nginx (bloqueo de rutas sensibles)"
code_env="$(curl -sk -o /dev/null -w '%{http_code}' "$URL/.env" 2>/dev/null || echo 000)"
[ "$code_env" = "404" ] || [ "$code_env" = "403" ] && ok "/.env → $code_env" || bad "/.env → $code_env (esperado 403/404)"

code_docs="$(curl -sk -o /dev/null -w '%{http_code}' "$URL/docs" 2>/dev/null || echo 000)"
[ "$code_docs" = "404" ] || [ "$code_docs" = "403" ] && ok "/docs → $code_docs" || bad "/docs → $code_docs"

code_bot="$(curl -sk -o /dev/null -w '%{http_code}' -A 'nikto' "$URL/api/health" 2>/dev/null || echo 000)"
[ "$code_bot" = "403" ] && ok "User-Agent nikto bloqueado (403)" || warn "Bot block: código $code_bot (nginx WAF puede variar)"

echo ""
echo "4. OpenAPI / métricas no públicas"
code_open="$(curl -sk -o /dev/null -w '%{http_code}' "$URL/openapi.json" 2>/dev/null || echo 000)"
[ "$code_open" = "404" ] || [ "$code_open" = "403" ] && ok "openapi.json no expuesto ($code_open)" || bad "openapi.json → $code_open"

code_metrics="$(curl -sk -o /dev/null -w '%{http_code}' "$URL/metrics" 2>/dev/null || echo 000)"
[ "$code_metrics" = "403" ] || [ "$code_metrics" = "404" ] && ok "/metrics protegido ($code_metrics)" || bad "/metrics → $code_metrics"

echo ""
echo "5. Base de datos — residuos HACKED"
if [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
  HACKED="$(
    docker compose -f "$COMPOSE_FILE" exec -T database \
      mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B "${MYSQL_DATABASE:-iespro_taller_app}" \
      -e "SELECT COUNT(*) FROM sucursales WHERE activo=1 AND (nombre LIKE '%HACKED%' OR direccion LIKE '%Hacker%');" \
      2>/dev/null || echo "?"
  )"
  if [ "$HACKED" = "0" ]; then
    ok "Sin sucursales HACKED activas"
  elif [ "$HACKED" = "?" ]; then
    warn "No se pudo consultar MySQL (¿contenedor database arriba?)"
  else
    bad "Hay $HACKED sucursal(es) HACKED activa(s) — ejecuta cleanup-pentest-data.sql"
  fi
else
  warn "MYSQL_ROOT_PASSWORD no en entorno — omitiendo check HACKED"
fi

echo ""
echo "6. Monitoreo (opcional)"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q prometheus; then
  ok "Prometheus corriendo"
else
  warn "Prometheus no activo (opcional: docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d)"
fi
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q grafana; then
  ok "Grafana corriendo"
else
  warn "Grafana no activo (opcional)"
fi

echo ""
echo "7. Postura de seguridad (API — evidencia en código)"
ctrl="$(curl -sk "$URL/api/security/controls" 2>/dev/null || true)"
if echo "$ctrl" | grep -q '"compliant":true'; then
  ok "GET /api/security/controls → compliant"
elif echo "$ctrl" | grep -q '"compliant"'; then
  bad "POSTURA no compliant — curl $URL/api/security/controls"
else
  bad "No se pudo leer /api/security/controls (¿backend actualizado?)"
fi

echo ""
echo "==> Resumen: $PASS OK, $FAIL fallos"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "Listo para pentest: URL=$URL ./scripts/pentest-selfcheck.sh"
