#!/usr/bin/env bash
# Respaldo de MySQL (producción Docker).
#
# Uso:
#   ./scripts/backup-mysql.sh
#   BACKUP_DIR=/var/backups/iespro ./scripts/backup-mysql.sh
#
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/iespro-mysql-${TIMESTAMP}.sql.gz"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${MYSQL_ROOT_PASSWORD:?Define MYSQL_ROOT_PASSWORD en .env}"
DB="${MYSQL_DATABASE:-iespro_taller_app}"

mkdir -p "$BACKUP_DIR"

docker compose -f "$COMPOSE_FILE" exec -T database \
  mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers "$DB" \
  | gzip > "$OUT"

echo "Backup guardado en: $OUT"
