# Guía de despliegue Docker — AI-NOC Copilot

Documento operativo para desarrollo, demostración y presentación del proyecto.
Cubre el modo **Docker (Opción B / entregable de curso)** y su convivencia con el
modo **venv local (Opción A / día a día)**.

> Stack: FastAPI + SQLite + Streamlit + Ollama nativo en el host.
> Ollama **no** corre dentro de Docker. El compose solo levanta backend y frontend.

---

## 1. Arquitectura del despliegue

```
                    ┌─────────────────────────────────────┐
                    │  Host (Windows)                     │
                    │                                     │
  generate_fake_    │   Ollama :11434                     │
  logs.py ──UDP─────┼──► 0.0.0.0:11434  ◄── host.docker.  │
  :5514             │              │         internal     │
                    │              │                      │
                    │  ┌───────────┴──────────┐           │
                    │  │ docker compose       │           │
                    │  │                      │           │
                    │  │  backend :8000       │           │
                    │  │  syslog  :5514/udp   │──volumen──│── backend_data (SQLite)
                    │  │         │            │           │
                    │  │  frontend :8501      │           │
                    │  │  (bind: dashboard.py │           │
                    │  │         + static/)   │           │
                    │  └──────────────────────┘           │
                    └─────────────────────────────────────┘
```

| Componente | Dónde corre | URL / puerto |
|------------|-------------|--------------|
| Backend API | Contenedor `ai-noc-backend` | http://localhost:8000 |
| Syslog UDP | Contenedor (mapeado al host) | `localhost:5514/udp` |
| Dashboard | Contenedor `ai-noc-frontend` | http://localhost:8501 |
| Ollama | **Host nativo** | http://localhost:11434 (desde el host); desde el contenedor → `host.docker.internal:11434` |
| SQLite | Volumen Docker `backend_data` | `/app/data/events.db` dentro del backend |

---

## 2. Prerrequisitos obligatorios (antes de `docker compose up`)

### 2.1 Ollama escuchando en todas las interfaces

El backend del contenedor **no** puede usar `127.0.0.1` del host. Debe alcanzar
Ollama vía `host.docker.internal`, y eso exige que Ollama bindee `0.0.0.0:11434`.

**Comprobar:**

```powershell
netstat -ano | findstr 11434
```

- Correcto: aparece `0.0.0.0:11434`
- Incorrecto: solo `127.0.0.1:11434` → el contenedor no conecta

**Levantar Ollama bien bindeado (sesión actual):**

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11434"
ollama serve
```

**Persistente (recomendado):** variable de entorno de usuario/sistema de Windows:

| Nombre | Valor |
|--------|--------|
| `OLLAMA_HOST` | `0.0.0.0:11434` |

Después reiniciar Ollama (o el PC). Así no hay que repetir el `$env:...` en cada sesión.

**Modelo esperado:** `my-qwen-3b:latest` (verificar con `ollama list`).

### 2.2 Liberar puertos 8000 y 5514

El backend de la Opción A (venv) y el de Docker **comparten** `8000` y `5514/udp`.
Si el venv sigue arriba, `docker compose up` falla con *port is already allocated*.

```powershell
# Detener backend local si estaba corriendo (Ctrl+C en esa terminal)
# Comprobar:
netstat -ano | findstr ":8000"
netstat -ano | findstr ":5514"
```

### 2.3 Docker Desktop en marcha

El daemon debe estar activo antes de cualquier comando `docker` / `docker compose`.

---

## 3. Comandos de despliegue

Ejecutar desde la **raíz del repositorio** (donde está `docker-compose.yml`).

### Primera vez o tras cambiar Dockerfile / requirements

```powershell
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Día a día (imágenes ya construidas)

```powershell
docker compose up -d
```

### Solo un servicio

```powershell
docker compose build frontend
docker compose up -d frontend

docker compose build backend
docker compose up -d backend
```

### Verificar punta a punta

```powershell
docker compose ps
curl http://localhost:8000/health
# Esperado: {"status":"ok"}  (o similar)

# Frontend responde (código HTTP)
curl -s -o $null -w "%{http_code}" http://localhost:8501

python scripts/generate_fake_logs.py --scenario bruteforce --count 10
```

URLs:

- Dashboard: http://localhost:8501  
- API Swagger: http://localhost:8000/docs  

---

## 4. Desarrollo: ¿cada cambio exige rebuild?

| Qué cambias | Acción |
|-------------|--------|
| `backend/app/**` | Ya está montado por volumen → `docker compose restart backend` (uvicorn en imagen no usa `--reload`) |
| `frontend/dashboard.py` o `frontend/static/**` | Con bind mounts en compose → Streamlit recarga solo; si no, `docker compose restart frontend` |
| `frontend/requirements.txt` o `frontend/Dockerfile` | `docker compose build frontend` → `up -d frontend` |
| `backend/requirements.txt` o `backend/Dockerfile` | `docker compose build backend` → `up -d backend` |
| `docker-compose.yml` | `docker compose up -d` (o `--force-recreate` del servicio afectado) |

### Volúmenes útiles del frontend (compose)

Para no rebuildar la UI en cada edición:

```yaml
frontend:
  volumes:
    - ./frontend/dashboard.py:/app/dashboard.py
    - ./frontend/static:/app/static
```

El backend ya monta el código de aplicación:

```yaml
backend:
  volumes:
    - ./backend/app:/app/app
    - backend_data:/app/data
```

### Estáticos (favicon, diagramas)

Archivos referenciados por el dashboard (p. ej. `arquitectura.svg`) deben vivir bajo
`frontend/static/` y referenciarse con ruta relativa al contenedor, por ejemplo
`static/arquitectura.svg`. No usar rutas absolutas de Windows.

---

## 5. Generación de logs sintéticos (con Docker o venv)

El script corre **en el host**, no dentro del contenedor. Envía UDP a
`127.0.0.1:5514`. Docker publica ese puerto al listener del backend.

```powershell
python scripts/generate_fake_logs.py --scenario normal --count 15
python scripts/generate_fake_logs.py --scenario bruteforce --count 10
python scripts/generate_fake_logs.py --scenario portscan --count 10
python scripts/generate_fake_logs.py --scenario beacon --count 10 --interval 0.5
python scripts/generate_fake_logs.py --scenario dns_dga --count 10
python scripts/generate_fake_logs.py --scenario dns_normal --count 10
python scripts/generate_fake_logs.py --scenario vpn_flapping --count 10
```

Escenarios con **IP fija por lote** (para correlación en el dashboard):
`bruteforce`, `portscan`, `beacon`, `dns_dga`.

Parámetros útiles: `--host`, `--port`, `--count`, `--interval`, `--scenario`.

---

## 6. Opción A (venv) vs Opción B (Docker): ¿hay que cambiar variables todo el tiempo?

**No**, si se separan bien responsabilidades.

| Variable / ajuste | Venv (Opción A) | Docker (Opción B) | ¿Conflictúa? |
|-------------------|-----------------|-------------------|--------------|
| `OLLAMA_HOST` del **proceso Ollama** | Ideal: `0.0.0.0:11434` siempre | Igual | No. Dejarlo en `0.0.0.0` sirve para ambos |
| `OLLAMA_HOST` del **backend** (cliente HTTP) | `backend/.env` → `http://localhost:11434` | Compose inyecta `http://host.docker.internal:11434` | No. Compose **pisa** al `.env` del contenedor |
| `BACKEND_URL` del frontend | `http://127.0.0.1:8000` (default en código o `frontend/.env`) | Compose: `http://backend:8000` | No. Solo aplica dentro del contenedor |
| Puertos 8000 / 5514 | Un solo dueño a la vez | Un solo dueño a la vez | **Sí hay que elegir:** o venv o Docker, no los dos a la vez |

### Flujo práctico recomendado

1. **Ollama siempre** con `OLLAMA_HOST=0.0.0.0:11434` (variable persistente de Windows).
2. **Desarrollo diario de código** → Opción A (venv + `--reload` / Streamlit local). Más rápido.
3. **Validar entregable / demo “como en producción del curso”** → parar venv, `docker compose up -d`.
4. No hace falta editar `backend/.env` al alternar: el compose define el entorno del contenedor.

```powershell
# Pasar de Docker → venv
docker compose down
cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
# otra terminal: streamlit run frontend\dashboard.py

# Pasar de venv → Docker
# Ctrl+C en backend y frontend locales
docker compose up -d
```

---

## 7. Particularidades y errores frecuentes

### 7.1 `ValueError: numpy.dtype size changed` (frontend)

Causa: `pandas==2.0.3` instalado contra un `numpy` 2.x en la imagen limpia.

Mitigación en `frontend/requirements.txt`:

```text
numpy==1.26.4
pandas==2.0.3
```

Rebuild del frontend tras el pin:

```powershell
docker compose build frontend --no-cache
docker compose up -d frontend
```

### 7.2 Backend no alcanza Ollama

- Ollama solo en `127.0.0.1` → fijar `0.0.0.0:11434`.
- Modelo distinto al de compose (`OLLAMA_MODEL=my-qwen-3b:latest`).
- Firewall bloqueando; menos habitual en local.

```powershell
curl http://localhost:11434/api/tags
docker compose logs backend --tail 80
```

### 7.3 Puerto ocupado

Detener el backend/frontend de venv o el compose anterior. No correr ambos stacks a la vez.

### 7.4 Imagen “sin usar” en Docker Desktop

La GUI a veces desincroniza el estado “en uso”. Confiar en:

```powershell
docker compose ps
docker ps -a
```

### 7.5 Tamaños de imagen

- Backend ~250–320 MB: razonable (`python:3.11-slim` + FastAPI).
- Frontend ~1 GB: esperable (Streamlit + pyarrow + pandas + plotly). No indica un fallo de configuración.
- No instalar `pytest` en la imagen de runtime del backend (dejarlo en deps de desarrollo).

### 7.6 Datos de demo

El volumen `backend_data` **persiste** entre `down` / `up`.

```powershell
# Reset total (borra eventos)
docker compose down -v
docker compose up -d
```

### 7.7 Historial de Builds en Docker Desktop

Son cachés/intentos de build (incluidos fallidos). Se pueden borrar sin afectar contenedores en ejecución:

```powershell
docker builder prune
```

---

## 8. Mantenimiento y depuración (cheatsheet)

```powershell
# Estado
docker compose ps
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs backend --tail 100

# Reinicios
docker compose restart backend
docker compose restart frontend
docker compose up -d --force-recreate frontend

# Rebuild selectivo
docker compose build frontend
docker compose build backend --no-cache

# Salud
curl http://localhost:8000/health
curl http://localhost:8000/events
curl http://localhost:11434/api/tags

# Inspección
docker images
docker volume ls
docker inspect ai-noc-backend
docker exec -it ai-noc-backend ls -la /app/data

# Limpieza segura (no borra volúmenes)
docker system prune
docker builder prune

# Limpieza agresiva de imágenes huérfanas (revisar antes)
docker image prune
```

**No usar** de forma habitual:

```powershell
docker system prune -a --volumes   # borra también backend_data
```

### Docker Scout

Escaneo de vulnerabilidades opcional desde Docker Desktop. Útil para la presentación
como buena práctica; no bloquea el MVP del curso. Priorizar Critical/High con fix
disponible en la base `python:3.11-slim` o en pins de pip.

---

## 9. Checklist de demo / presentación

1. Docker Desktop en ejecución.  
2. `netstat` muestra `0.0.0.0:11434`.  
3. `ollama list` incluye `my-qwen-3b:latest`.  
4. Ningún uvicorn/streamlit local ocupando 8000/8501/5514.  
5. `docker compose up -d` → ambos servicios healthy/running.  
6. http://localhost:8000/health y http://localhost:8501 OK.  
7. `python scripts/generate_fake_logs.py --scenario bruteforce --count 10`.  
8. En el dashboard: eventos visibles, correlacionar, explicar con IA.  
9. (Opcional) Mostrar diagrama en `static/`, volumen persistente y que Ollama no está en el compose.

---

## 10. Mensajes clave para explicar a terceros

- **Air-gapped por diseño:** el LLM es local (Ollama en el host); no hay APIs cloud en el camino de análisis.  
- **Docker solo empaqueta API + UI** para el entregable; el modelo no se duplica en un contenedor (SSD, GPU/CPU del host, simplicidad de red).  
- **Detección determinista + LLM que explica:** beaconing (CV de intervalos), DGA (entropía); el modelo no decide solo si algo es malicioso.  
- **Logs de prueba:** generador con formato filterlog verificado; no se usa pfSense de producción en el laboratorio.  
- **Datos:** SQLite en volumen Docker; sobrevive a reinicios del compose hasta `down -v`.

---

## 11. Referencia rápida de archivos

| Archivo | Rol |
|---------|-----|
| `docker-compose.yml` | Orquestación backend + frontend, env de Ollama, healthcheck, volúmenes |
| `backend/Dockerfile` | Imagen API |
| `frontend/Dockerfile` | Imagen Streamlit |
| `backend/requirements.txt` | Deps de **runtime** del backend (sin pytest) |
| `frontend/requirements.txt` | streamlit, httpx, plotly, **numpy pin**, pandas |
| `backend/.env` / `.env.example` | Uso local (venv); en Docker mandan las variables del compose |
| `scripts/generate_fake_logs.py` | UDP → `:5514` desde el host |
| `frontend/static/` | Favicon, diagramas (p. ej. arquitectura) |

---

*Documento alineado con las decisiones de SPEC/README del proyecto y la experiencia de puesta en marcha Docker (compatibilidad numpy/pandas, bind mounts de UI, Ollama en 0.0.0.0, logs sintéticos por UDP).*
