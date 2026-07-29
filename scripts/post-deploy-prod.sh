#!/usr/bin/env bash
# Post-despliegue en producción: build, cleanup forense, verificación.
#
# Uso en VPS:
#   cd ~/taller-ollama
#   ./scripts/post-deploy-prod.sh
#
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "==> Levantando servicios..."
docker compose -f "$COMPOSE_FILE" up -d --build backend frontend

echo ""
echo "==> Verificando health del backend..."
HEALTH_OK=0
for _ in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T backend \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" \
    >/dev/null 2>&1; then
    echo "OK: backend respondiendo en /api/health"
    HEALTH_OK=1
    break
  fi
  sleep 2
done

if [ "$HEALTH_OK" -ne 1 ]; then
  echo "ERROR: el backend no responde — revisa logs:"
  docker compose -f "$COMPOSE_FILE" logs backend --tail 40 || true
  exit 1
fi

if [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
  echo ""
  echo "==> Limpieza forense (cleanup-pentest-data.sql)..."
  docker compose -f "$COMPOSE_FILE" exec -T database \
    mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "${MYSQL_DATABASE:-iespro_taller_app}" \
    < scripts/cleanup-pentest-data.sql
fi

if [ -f docker-compose.monitoring.yml ]; then
  echo ""
  echo "==> Levantando monitoreo (Prometheus + Grafana)..."
  docker compose -f "$COMPOSE_FILE" -f docker-compose.monitoring.yml up -d 2>/dev/null || \
    warn_monitoring="No se pudo levantar monitoring (¿GRAFANA_ADMIN_PASSWORD en .env?)"
  [ -z "${warn_monitoring:-}" ] && echo "OK: stack de monitoreo iniciado (localhost:9090, :3001)"
fi

echo ""
./scripts/verify-prod-security.sh

echo ""
echo "Post-despliegue completado."
echo "Siguiente: URL=https://200-234-226-167.sslip.io EMAIL=... PASS='...' ./scripts/pentest-master.sh"
