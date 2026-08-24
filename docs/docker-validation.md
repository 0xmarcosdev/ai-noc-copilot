# Validación Docker — AI-NOC Copilot

> Inspección estática realizada el 23 ago 2026. Este equipo no tiene Docker
> instalado, así que la validación es por revisión de código línea por línea,
> no por build real. No se puede verificar en runtime.

## 1. Dependencias: código vs Dockerfiles

### Backend (`backend/Dockerfile`)

El Dockerfile hace `COPY requirements.txt .` y luego `pip install -r requirements.txt`.
Se verificaron TODOS los imports de los archivos que se copian al contenedor
(`app/main.py`, `app/models.py`, `app/llm_service.py`, `app/syslog_listener.py`,
`app/dns_heuristics.py`, `app/dns_parsing.py`):

| Import | Paquete pip | En requirements.txt |
|---|---|---|
| fastapi | fastapi==0.115.0 | ✅ |
| uvicorn | uvicorn[standard]==0.30.6 | ✅ |
| httpx | httpx==0.27.2 | ✅ |
| sqlmodel | sqlmodel==0.0.22 | ✅ |
| pydantic | (dependencia de fastapi) | ✅ implícito |
| sqlalchemy | (dependencia de sqlmodel) | ✅ implícito |
| dotenv | python-dotenv==1.0.1 | ✅ |
| asyncio, collections, re, math, etc. | stdlib | ✅ |

**Veredicto backend:** ✅ Todas las dependencias están cubiertas.

### Frontend (`frontend/Dockerfile`)

El Dockerfile ahora hace `COPY requirements.txt .` y `pip install -r requirements.txt`
(README.md línea 99 actualizado para Opción A). Se verificaron los imports
de `dashboard.py`:

| Import | Paquete pip | En requirements.txt |
|---|---|---|
| streamlit | streamlit==1.39.0 | ✅ |
| httpx | httpx==0.27.2 | ✅ |
| plotly.graph_objects | plotly==6.0.1 | ✅ |
| csv, io, json, os, datetime | stdlib | ✅ |

**Veredicto frontend:** ✅ Todas las dependencias están cubiertas.

## 2. Variables de entorno

### Backend (`main.py` + `llm_service.py`)

| Variable | Default en código | En docker-compose.yml |
|---|---|---|
| `DB_PATH` | `./data/events.db` | `/app/data/events.db` ✅ |
| `SYSLOG_PORT` | `5514` | `5514` ✅ |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | `http://host.docker.internal:11434` ✅ |
| `OLLAMA_MODEL` | `my-qwen-3b:latest` | `my-qwen-3b:latest` ✅ |
| `CORRELATION_THRESHOLD` | `5` | No seteado (usa default) ✅ |
| `MAX_INGEST_LINES` | `5000` | No seteado (usa default) ✅ |

### Frontend (`dashboard.py`)

| Variable | Default en código | En docker-compose.yml |
|---|---|---|
| `BACKEND_URL` | `http://127.0.0.1:8000` | `http://backend:8000` ✅ |

**Veredicto variables de entorno:** ✅ Todas tienen default razonable o están seteadas en compose.

## 3. Healthcheck del backend

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
```

- Endpoint `/health` existe: `main.py` línea 125-127 → `return {"status": "ok"}` ✅
- Python 3.11-slim trae `urllib.request` (stdlib) ✅
- No depende de `curl` (que no viene en la imagen) ✅

**Veredicto healthcheck:** ✅ Correcto.

## 4. .dockerignore

### `backend/.dockerignore`
Excluye: `.venv/`, `data/`, `.env`, `.env.example`, `__pycache__/`, `.pytest_cache/`, `tests/`, `file__memory_`

**Veredicto:** ✅ Correcto — no se copian el venv (~400MB), la DB, ni tests al contenedor.

### `frontend/.dockerignore`
Excluye: `.env`, `__pycache__/`, `*.pyc`

**Veredicto:** ✅ Correcto — no se copia el .env al contenedor.

## 5. docker-compose.yml

- `backend.build: ./backend` ✅
- `frontend.build: ./frontend` ✅
- `backend.volumes`: `./backend/app:/app/app` (hot-reload en desarrollo) + `backend_data:/app/data` (persistencia) ✅
- `frontend.depends_on: backend: condition: service_healthy` ✅ (espera a que el backend esté healthy)
- `extra_hosts: host.docker.internal:host-gateway` ✅ (permite que el contenedor alcance Ollama en el host)
- Puertos: `8000:8000`, `5514:5514/udp`, `8501:8501` ✅

**Veredicto compose:** ✅ Correcto.

## 6. Limitaciones conocidas (no resueltas)

1. **No se puede probar `docker compose up` en este equipo** — validación por inspección estática únicamente.
2. **Ollama debe estar bindeado a `0.0.0.0:11434`** — documentado en README y docker-compose.yml, pero no se puede verificar sin Docker corriendo.
3. **Migración de esquema** (`correlation_group` en SQLite existente) — sigue sin resolverse (ver SPEC §7). Si alguien usó una versión anterior de la DB, debe borrar el archivo `.db`.
4. **plotly en el frontend** — antes de esta corrección, el Dockerfile del frontend NO instalaba plotly (se agregó solo a `backend/requirements.txt`). Corregido en esta sesión creando `frontend/requirements.txt`.
