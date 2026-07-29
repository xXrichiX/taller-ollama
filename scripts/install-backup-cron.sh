#!/usr/bin/env bash
# Instala respaldo diario de MySQL (03:00). Ejecutar una vez en el VPS.
#
#   cd ~/taller-ollama && ./scripts/install-backup-cron.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="${BACKUP_LOG:-/var/log/iespro-mysql-backup.log}"
CRON_LINE="0 3 * * * cd $ROOT && ./scripts/backup-mysql.sh >> $LOG_FILE 2>&1"

( crontab -l 2>/dev/null | grep -v 'backup-mysql.sh' || true
  echo "$CRON_LINE"
) | crontab -

echo "OK: cron instalado — backup MySQL diario a las 03:00"
echo "  Log: $LOG_FILE"
crontab -l | grep backup-mysql || true
