#!/usr/bin/env bash
# Post-despliegue en producción: rebuild y verificación básica.
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
for _ in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T backend \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" \
    >/dev/null 2>&1; then
    echo "OK: backend respondiendo en /api/health"
    echo ""
    echo "Post-despliegue completado."
    exit 0
  fi
  sleep 2
done

echo "ERROR: el backend no respondió a tiempo. Revisa: docker compose -f $COMPOSE_FILE logs backend"
exit 1
