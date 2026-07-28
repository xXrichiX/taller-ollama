# Cloudflare CDN (opcional) — IESPRO Taller

El proyecto ya usa **Cloudflare Turnstile** para CAPTCHA en registro. Este documento describe cómo poner **todo el sitio** detrás del proxy naranja de Cloudflare (CDN + DDoS + WAF gestionado), además del WAF nginx que ya corre en el VPS.

## Cuándo hacerlo

| Situación | Recomendación |
|-----------|---------------|
| Entrega académica / VPS sslip.io | **Opcional** — nginx WAF + Caddy ya cubren el alcance |
| Producción con dominio propio | **Recomendado** — capa extra DDoS y WAF gestionado |
| Bloqueo SMTP saliente (puerto 587) | Cloudflare **no** desbloquea SMTP; usar API de email (Resend/Brevo) por HTTPS |

## Pasos (dominio propio o sslip.io)

### 1. Añadir sitio en Cloudflare

1. Cuenta en [dash.cloudflare.com](https://dash.cloudflare.com).
2. **Add a site** → tu dominio (ej. `taller.tudominio.com` o `200-234-226-167.sslip.io`).
3. Plan Free es suficiente para el taller.

### 2. DNS

| Tipo | Nombre | Contenido | Proxy |
|------|--------|-----------|-------|
| A | `@` o subdominio | IP del VPS (ej. `200.234.226.167`) | Proxied (nube naranja) |

### 3. SSL/TLS en Cloudflare

- **SSL/TLS → Overview:** `Full (strict)` si Caddy tiene certificado válido en origen.
- **Edge Certificates:** activar *Always Use HTTPS*.

### 4. Variables en el VPS (`.env`)

```bash
PUBLIC_URL=https://tu-dominio.com
PUBLIC_DOMAIN=tu-dominio.com
TRUST_PROXY_HEADERS=1
BEHIND_CLOUDFLARE=1
```

### 5. Redesplegar

```bash
cd ~/taller-ollama
docker compose -f docker-compose.prod.yml up -d --build
```

### 6. Verificar

```bash
curl -s https://tu-dominio.com/api/security/controls | jq '.edge_cdn'
# cloudflare_proxy: true

curl -sI https://tu-dominio.com | grep -i cf-ray
# debe aparecer CF-RAY (tráfico pasa por Cloudflare)
```

## WAF Cloudflare (opcional)

En plan Free, reglas básicas de bot fight mode:

- **Security → Bots → Bot Fight Mode:** On
- **Security → Settings → Security Level:** Medium

Reglas custom avanzadas requieren plan de pago; el WAF nginx del repo sigue siendo la capa en origen.

## Turnstile (ya integrado)

Turnstile y proxy CDN son independientes:

- `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` en `.env`
- CSP en `web/nginx.conf` ya permite `challenges.cloudflare.com`

## Qué no resuelve Cloudflare

- Verificación de email por SMTP (puerto 587 bloqueado en muchos VPS)
- Sustituir auditoría HMAC, JWT RS256 ni rate limits de la aplicación

## Evidencia para auditoría

Con `BEHIND_CLOUDFLARE=1`, `/api/security/controls` reporta:

```json
"edge_cdn": {
  "nginx_waf": true,
  "cloudflare_proxy": true,
  "turnstile_active": true
}
```

Sin activar el proxy, `cloudflare_proxy: false` es **aceptable**: el informe marca WAF nginx como **CUMPLE**; Cloudflare es mejora documentada.
