#!/bin/sh
set -eu

IP="${TLS_SAN_IP:?TLS_SAN_IP requerido en .env}"
mkdir -p /certs

if [ -f /certs/server.crt ] && [ -f /certs/server.key ]; then
  echo "Certificados TLS ya existen en /certs"
  exit 0
fi

apk add --no-cache openssl >/dev/null

openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout /certs/server.key \
  -out /certs/server.crt \
  -subj "/CN=${IP}" \
  -addext "subjectAltName=IP:${IP}"

chmod 644 /certs/server.crt
chmod 600 /certs/server.key
echo "Certificado TLS generado para IP ${IP}"
