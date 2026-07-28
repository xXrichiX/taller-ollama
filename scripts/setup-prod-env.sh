#!/usr/bin/env bash
# Completa .env de producción (MYSQL_APP_PASSWORD, JWT, seguridad).
# Uso en VPS: cd ~/taller-ollama && ./scripts/setup-prod-env.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ENV_FILE=".env"
KEYS_DIR="iespro_taller/data/keys"

if [ ! -f "$ENV_FILE" ]; then
  echo "No existe .env — copia .env.example primero."
  exit 1
fi

# MYSQL_APP_PASSWORD
if ! grep -q '^MYSQL_APP_PASSWORD=' "$ENV_FILE" 2>/dev/null; then
  APP_PW="$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"
  echo "MYSQL_APP_PASSWORD=$APP_PW" >> "$ENV_FILE"
  echo "Añadido MYSQL_APP_PASSWORD al .env"
else
  APP_PW="$(grep '^MYSQL_APP_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)"
  echo "MYSQL_APP_PASSWORD ya existe en .env"
fi

grep -q '^MYSQL_USER=' "$ENV_FILE" || echo "MYSQL_USER=iespro_app" >> "$ENV_FILE"
grep -q '^TRUST_PROXY_HEADERS=' "$ENV_FILE" || echo "TRUST_PROXY_HEADERS=1" >> "$ENV_FILE"
grep -q '^SESSION_IDLE_SECONDS=' "$ENV_FILE" || echo "SESSION_IDLE_SECONDS=86400" >> "$ENV_FILE"
grep -q '^MAX_TOOL_CALLS_PER_TURN=' "$ENV_FILE" || echo "MAX_TOOL_CALLS_PER_TURN=8" >> "$ENV_FILE"

# Claves JWT RS256 (persisten en volumen Docker)
mkdir -p "$KEYS_DIR"
if [ ! -s "$KEYS_DIR/jwt_private.pem" ]; then
  openssl genrsa -out "$KEYS_DIR/jwt_private.pem" 2048
  openssl rsa -in "$KEYS_DIR/jwt_private.pem" -pubout -out "$KEYS_DIR/jwt_public.pem"
  chmod 600 "$KEYS_DIR/jwt_private.pem" "$KEYS_DIR/jwt_public.pem"
  echo "Claves JWT generadas en $KEYS_DIR/"
else
  echo "Claves JWT ya existen en $KEYS_DIR/"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${MYSQL_ROOT_PASSWORD:?Define MYSQL_ROOT_PASSWORD en .env}"

echo ""
echo "Creando/actualizando usuario MySQL iespro_app..."
docker compose -f docker-compose.prod.yml exec -T database \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "
CREATE USER IF NOT EXISTS 'iespro_app'@'%' IDENTIFIED BY '${MYSQL_APP_PASSWORD}';
GRANT ALL PRIVILEGES ON ${MYSQL_DATABASE:-iespro_taller_app}.* TO 'iespro_app'@'%';
FLUSH PRIVILEGES;
"

echo ""
echo "Listo. Siguiente:"
echo "  docker compose -f docker-compose.prod.yml up -d --build backend frontend"
echo "  ./scripts/post-deploy-prod.sh   # cleanup + verificación forense"
echo "  URL=https://... EMAIL=... PASS='...' ./scripts/pentest-master.sh"
