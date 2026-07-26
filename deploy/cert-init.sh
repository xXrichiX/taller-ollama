#!/bin/sh
set -eu

IP="${TLS_SAN_IP:-200.234.226.167}"
mkdir -p /certs

if [ -s /certs/server.crt ] && [ -s /certs/server.key ]; then
  echo "Certificados TLS ya existen."
  exit 0
fi

echo "Generando certificado TLS para IP ${IP}..."
apk add --no-cache openssl

cat >/tmp/openssl.cnf <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = ${IP}

[v3_req]
subjectAltName = IP:${IP}
EOF

openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout /certs/server.key \
  -out /certs/server.crt \
  -config /tmp/openssl.cnf \
  -extensions v3_req

chmod 644 /certs/server.crt
chmod 600 /certs/server.key
echo "Certificado listo."
