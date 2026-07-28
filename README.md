# IESPRO-Taller

Taller mecánico con **IA local (Ollama)**: web React, API FastAPI, MySQL, RAG multi-agente.

## Requisitos

- Python **3.12**, MySQL 8, Ollama (`llama3.2:3b`, `nomic-embed-text`)
- Docker (opcional, recomendado)

Login demo: `admin@iespro.mx` / `admin1234`

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
# Edita: MYSQL_ROOT_PASSWORD, PUBLIC_URL=http://TU_IP

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
docker-compose.prod.yml  # Producción (Ollama en el servidor)
```

ChromaDB: `db_vectorial/` (local) o volumen Docker `chroma_data` (prod).

---

## Seguridad (producción)

Variables en `.env` / `docker-compose.prod.yml`:

| Variable | Prod recomendado | Descripción |
|----------|------------------|-------------|
| `APP_ENV` | `production` | Errores Pydantic genéricos |
| `REGISTRATION_ENABLED` | `0` | Cierra registro público |
| `REGISTRATION_INVITE_CODE` | opcional | Código para registrar si está habilitado |
| `RATE_LIMIT_ENABLED` | `1` | Límite de peticiones por IP |
| `SESSION_COOKIE_SECURE` | `1` | Cookie de sesión solo por HTTPS |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | opcional | CAPTCHA en registro |

Incluye: bcrypt, rate limiting, cookies HttpOnly, cabeceras CSP, observabilidad solo dueño, inventario por rol, Turnstile opcional en registro.

### Modelo de amenazas (asistente IA)

El chat **no ejecuta SQL arbitrario**. Usa un catálogo cerrado de herramientas con **tres capas de control**:

1. **RBAC por rol** — el LLM solo ve las tools permitidas (`tool_policy.py`): clientes no listan inventario; mecánicos no listan clientes; solo el dueño usa `listar_clientes` / `buscar_cliente`.
2. **Scope de datos** — cada tool fuerza `id_sucursal` / `id_isla` del usuario (`tools_service._scope_arguments`); el chat valida sucursal en API (`chat_scope.py`, anti-IDOR).
3. **Minimización** — listados masivos ocultan email/teléfono (`[oculto]`), máximo 25 filas; guardrails bloquean extracción masiva y SQL en español/inglés.

En producción no se exponen `tool_calls`, `route` ni métricas internas. Prompt injection se mitiga con guardrails y ruta `blocked`; el riesgo residual de LLM es inherente al producto, no un backdoor a la BD.

### Auto-auditoría (pentest)

```bash
# Rápido (11 secciones)
URL=https://tu-servidor.sslip.io ./scripts/pentest-selfcheck.sh

# Completo + reporte Markdown
URL=https://tu-servidor.sslip.io EMAIL=tu@mail.com PASS='...' ./scripts/pentest-master.sh
# → pentest-reports/pentest-*.md

# Limpieza forense tras pentest del profesor
docker compose -f docker-compose.prod.yml exec -T database \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" iespro_taller_app \
  < scripts/cleanup-pentest-data.sql
```

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
