# IESPRO-Taller

Taller mecánico con **IA local (Ollama)**: web React, API FastAPI, MySQL, RAG multi-agente.

## Requisitos

- Python **3.12**, MySQL 8, Ollama (`llama3.2:3b`, `nomic-embed-text`)
- Docker (opcional, recomendado)

**No hay credenciales por defecto en producción.** Crea usuarios con el seeder o registro controlado.

---

## Desarrollo local

```bash
# 1. MySQL encendido + Ollama con modelos descargados

# 2. Backend
cd iespro_taller
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# 3. Frontend
cd ../web && npm install && npm run dev
```

Web: http://localhost:5173 · API: http://localhost:8000

---

## Docker (local)

```bash
cp .env.example .env
docker compose up --build
```

Web: http://localhost:3000

---

## Despliegue VPS (Oracle / Hetzner / etc.)

Mínimo: **8 GB RAM**, Ubuntu 22.04, puertos **22** y **80**.

```bash
git clone https://github.com/xXrichiX/taller-ollama.git
cd taller-ollama
cp .env.example .env
# Edita obligatorio: MYSQL_ROOT_PASSWORD, MYSQL_APP_PASSWORD, PUBLIC_URL, PUBLIC_DOMAIN, ACME_EMAIL

docker compose -f docker-compose.prod.yml up -d --build
```

Primera vez tarda ~15 min (descarga modelos Ollama). Progreso:

```bash
docker compose -f docker-compose.prod.yml logs -f ollama-init
```

Seeder (sem 7): `docker compose -f docker-compose.prod.yml exec backend python seeder.py --count 10000 --sync-rag`

Evaluador: `docker compose -f docker-compose.prod.yml exec backend python evaluar_agente.py`

---

## Estructura

```
iespro_taller/     # Backend Python (api, services, db, sql)
web/               # Frontend React + Vite
docker-compose.yml # Dev (Ollama en tu Mac)
docker-compose.prod.yml  # VPS académico (Ollama en el servidor; APP_ENV endurecido)
```

ChromaDB: `db_vectorial/` (local) o volumen Docker `chroma_data` (prod).

---

## Seguridad

`docker-compose.prod.yml` despliega la app en modo endurecido (`APP_ENV=production`). **Matriz de aprobación con criterio empresarial estricto:** [docs/SECURITY.md](docs/SECURITY.md) — todos los hallazgos críticos/altos del informe en **CUMPLE**; madurez enterprise (SIEM, WAF comercial) clasificada como evolución futura.

Variables en `.env` / `docker-compose.prod.yml`:

| Variable | Prod recomendado | Descripción |
|----------|------------------|-------------|
| `MYSQL_APP_PASSWORD` | ≥16 chars aleatorios | Usuario dedicado `iespro_app` (no root) |
| `MYSQL_ROOT_PASSWORD` | ≥16 chars aleatorios | Solo admin/backup MySQL |
| `APP_ENV` | `production` | Errores Pydantic genéricos |
| `TRUST_PROXY_HEADERS` | `1` | Rate limit por IP real detrás de Caddy |
| `REGISTRATION_ENABLED` | `0` | Cierra registro público |
| `REGISTRATION_INVITE_CODE` | opcional | Código para registrar si está habilitado |
| `RATE_LIMIT_ENABLED` | `1` | Límite de peticiones por IP |
| `SESSION_COOKIE_SECURE` | `1` | Cookie de sesión solo por HTTPS |
| `SESSION_IDLE_SECONDS` | `86400` | Expira sesión inactiva en servidor |
| `MAX_TOOL_CALLS_PER_TURN` | `8` | Tope de tools IA por turno |
| `JWT_PRIVATE_KEY_PEM` / `JWT_PUBLIC_KEY_PEM` | prod | Firma RS256 (o volumen `data/keys/`) |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | opcional | CAPTCHA en registro |

Incluye: bcrypt, rate limiting por IP real, cookies HttpOnly, cabeceras CSP, HSTS, usuario MySQL dedicado, validación de config en arranque prod, observabilidad solo dueño, inventario por rol, Turnstile opcional en registro.

### Respaldo MySQL (VPS)

```bash
chmod +x scripts/backup-mysql.sh
./scripts/backup-mysql.sh
# → backups/iespro-mysql-YYYYMMDD-HHMMSS.sql.gz
```

Programa esto con cron en el VPS (diario recomendado).

### Checklist pre-despliegue VPS

1. `.env` con `MYSQL_ROOT_PASSWORD` y `MYSQL_APP_PASSWORD` ≥16 caracteres aleatorios
2. `REGISTRATION_ENABLED=0` (o invite + Turnstile)
3. `PUBLIC_URL` y `PUBLIC_DOMAIN` con **https://**
4. `./scripts/setup-prod-env.sh` y `./scripts/post-deploy-prod.sh` tras el primer deploy
5. Backup probado con `./scripts/backup-mysql.sh`
6. Sin credenciales demo en la BD (`init_db` elimina `admin@iespro.mx` legacy)

Documentación completa: [docs/SECURITY.md](docs/SECURITY.md)

### Modelo de amenazas (asistente IA)

El chat **no ejecuta SQL arbitrario**. Usa un catálogo cerrado de herramientas con **tres capas de control**:

1. **RBAC por rol** — el LLM solo ve las tools permitidas (`tool_policy.py`): clientes no listan inventario; mecánicos no listan clientes; solo el dueño usa `listar_clientes` / `buscar_cliente`.
2. **Scope de datos** — cada tool fuerza `id_sucursal` / `id_isla` del usuario (`tools_service._scope_arguments`); el chat valida sucursal en API (`chat_scope.py`, anti-IDOR).
3. **Minimización** — listados masivos ocultan email/teléfono (`[oculto]`), máximo 25 filas; guardrails bloquean extracción masiva y SQL en español/inglés.

En modo endurecido (`APP_ENV=production`) no se exponen `tool_calls`, `route` ni métricas internas. Prompt injection se mitiga con guardrails y ruta `blocked`; el riesgo residual de LLM es inherente al producto, no un backdoor a la BD. La defensa en capas **no** sustituye un programa formal de seguridad de IA (red team periódico).

Tests unitarios (scope del chat):

```bash
cd iespro_taller && python -m unittest discover -s tests -v
```

---

## Terminal (opcional)

```bash
cd iespro_taller && source .venv/bin/activate
python agent_cli.py          # function calling en consola
python evaluar_agente.py     # LLM-as-judge + PDF
```
