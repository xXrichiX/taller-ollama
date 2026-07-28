#!/usr/bin/env bash
# Respuesta a incidente — revisión forense post-pentest o compromiso.
#
# Uso:
#   ./scripts/forensics-post-incident.sh
#
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${MYSQL_ROOT_PASSWORD:?Define MYSQL_ROOT_PASSWORD en .env}"
DB="${MYSQL_DATABASE:-iespro_taller_app}"
REPORT_DIR="${REPORT_DIR:-./pentest-reports}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="${REPORT_DIR}/forensics-${TS}.md"

mkdir -p "$REPORT_DIR"

{
  echo "# Informe forense IESPRO-Taller"
  echo ""
  echo "Fecha: $(date -Iseconds)"
  echo ""
  echo "## 1. Usuarios recientes"
  docker compose -f "$COMPOSE_FILE" exec -T database \
    mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$DB" -e \
    "SELECT id, nombre, email, id_rol, activo, id_sucursal FROM usuarios ORDER BY id DESC LIMIT 20;"

  echo ""
  echo "## 2. Sucursales sospechosas (nombre HACK / TEST / PENTEST)"
  docker compose -f "$COMPOSE_FILE" exec -T database \
    mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$DB" -e \
    "SELECT id, nombre, direccion, id_propietario FROM sucursales WHERE nombre REGEXP '(?i)(hack|pentest|injected|evil)';" || true

  echo ""
  echo "## 3. Auditoría reciente (si existe tabla)"
  docker compose -f "$COMPOSE_FILE" exec -T database \
    mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$DB" -e \
    "SELECT id, id_usuario, accion, recurso, ip, resultado, creado_en FROM audit_logs ORDER BY id DESC LIMIT 50;" 2>/dev/null || echo "(tabla audit_logs aún no creada)"

  echo ""
  echo "## 4. Acciones recomendadas"
  echo "- Rotar MYSQL_ROOT_PASSWORD y MYSQL_APP_PASSWORD en .env"
  echo "- Regenerar claves JWT (data/keys o JWT_*_PEM)"
  echo "- Reiniciar backend para invalidar sesiones en memoria"
  echo "- Restaurar backup si hay datos corruptos: ./scripts/backup-mysql.sh"
  echo "- Ejecutar cleanup: scripts/cleanup-pentest-data.sql"
} | tee "$OUT"

echo "Informe: $OUT"
