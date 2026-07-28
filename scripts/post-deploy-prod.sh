#!/usr/bin/env bash
# Post-despliegue en producción: limpieza forense + verificación.
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

: "${MYSQL_ROOT_PASSWORD:?Define MYSQL_ROOT_PASSWORD en .env}"
DB="${MYSQL_DATABASE:-iespro_taller_app}"

echo "==> Levantando servicios (si hace falta)..."
docker compose -f "$COMPOSE_FILE" up -d --build backend frontend

echo ""
echo "==> Ejecutando limpieza forense (cleanup-pentest-data.sql)..."
docker compose -f "$COMPOSE_FILE" exec -T database \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$DB" \
  < scripts/cleanup-pentest-data.sql

echo ""
echo "==> Verificando residuos HACKED_SUCURSAL..."
HACKED_COUNT="$(
  docker compose -f "$COMPOSE_FILE" exec -T database \
    mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -B "$DB" \
    -e "SELECT COUNT(*) FROM sucursales WHERE activo = 1 AND (nombre LIKE '%HACKED%' OR direccion LIKE '%Hacker%');"
)"

if [ "${HACKED_COUNT:-0}" -gt 0 ]; then
  echo "ERROR: Aún hay ${HACKED_COUNT} sucursal(es) HACKED activa(s). Revisa cleanup-pentest-data.sql"
  exit 1
fi
echo "OK: sin sucursales HACKED activas."

echo ""
echo "==> Generando informe forense..."
./scripts/forensics-post-incident.sh

echo ""
echo "Post-despliegue completado."
echo "Siguiente: URL=https://tu-dominio EMAIL=... PASS='...' ./scripts/pentest-master.sh"
