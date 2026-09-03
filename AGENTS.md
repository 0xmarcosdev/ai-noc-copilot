# AGENTS.md — AI-NOC Copilot

Copiloto local air-gapped de logs de pfSense (FastAPI + SQLModel/SQLite + Streamlit + Ollama nativo). Proyecto final de curso (entrega 4 sept 2026). **Todo el repo está en español** — documentación, comentarios, prompts y mensajes de commit se escriben en español.

## Punto de partida

- `docs/SPEC.md` — fuente de verdad técnica; `ROADMAP.md` — checklist operativo de fases; `DEVLOG.md` — diario de sesiones. **`SPEC.md` §11 contiene instrucciones explícitas para asistentes de IA**; respetarlas. Si un cambio propuesto contradice una decisión ya tomada ahí, decirlo explícitamente antes de proceder, no reemplazarla en silencio.
- El repo corre con el **generador de logs sintéticos**, no con pfSense real (los reales están en producción).
- **No agregar dependencias de servicios en la nube.** Todo debe funcionar air-gapped -- es un requisito de diseño, no una preferencia.

## Arquitectura (gotchas no obvios)

- `backend/app/main.py` es el único entrypoint (`uvicorn app.main:app`). Escucha syslog UDP en `5514` (tarea asíncrona en `syslog_listener.py`).
- **`NetworkEvent.source_ip` NO es la IP del atacante**: es la IP del paquete UDP de syslog (el propio pfSense). Toda correlación extrae la IP real del `raw_message` con regex (`extract_attacker_ip` en `main.py:51`). No cambiar esto a `source_ip`.
- **La detección es determinista, el LLM solo explica**: beaconing = coeficiente de variación de intervalos (`main.py`), DGA = entropía de Shannon (`dns_heuristics.py`). El LLM recibe el hallazgo ya detectado y redacta la explicación. No pedirle al LLM que decida solo si algo es malicioso.
- **Contrato del LLM**: 4 claves JSON estrictas (`severity`, `event_type`, `explanation`, `recommended_action`), prompts en `backend/app/prompts/*.txt`, llamado con `"format": "json"` y `temperature: 0.1`. No cambiar el contrato sin avisar explícitamente que rompe los consumidores en `main.py` (punto de acoplamiento más frágil).
- **`classify_port_pattern` (main.py) es determinista, no re-analiza con LLM**: clasifica `fuerza_bruta` / `escaneo_puertos` / `None` según la proporción de puertos destino distintos en el grupo (`MIN_EVENTS_FOR_PORT_PATTERN`, `BRUTEFORCE_MAX_RATIO`, `PORTSCAN_MIN_RATIO` al inicio del archivo). El resultado se pasa como texto de contexto al prompt del LLM, nunca al revés.
- **`SQLModel.metadata.create_all()` no migra columnas nuevas en SQLite existente.** Si agregás un campo a `NetworkEvent` (como `correlation_group`), una DB vieja no lo va a tener y va a fallar en runtime, no en el `lifespan`. En desarrollo la solución es borrar el `.db` y dejar que se recree; no hay migración automática todavía (ver limitación documentada en `SPEC.md` §7).
- **Ollama corre nativo en el host, NO en Docker.** `docker-compose.yml` solo levanta backend+frontend y es solo para el entregable del curso; el desarrollo diario corre con venv. El modelo real de desarrollo es `my-qwen-3b:latest` (`.env.example`, SPEC, scripts) -- si ves `qwen2.5:3b-instruct` en algún lado, es un valor viejo, corregirlo a `my-qwen-3b:latest`.
- La navegación del dashboard usa st.radio + session_state.main_tab, no st.tabs (los tabs de Streamlit no conservan la pestaña al rerun).
- No asumir que correlation-history trae explanation; la UI puede usar caché corr_expl.

## Comandos

```powershell
# Backend (requiere backend/.env, se carga solo via python-dotenv)
cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
# o: scripts\start-backend.ps1  (frontend: start-frontend.ps1, ambos: start-all.ps1)

# Tests (venv; NO necesita Ollama, el LLM se mockea)
cd backend; .\.venv\Scripts\python.exe -m pytest tests -v

# Lint (ruff, config en pyproject.toml)
cd backend; .\.venv\Scripts\ruff.exe check

# Logs sintéticos (requiere backend corriendo)
python scripts/generate_fake_logs.py --scenario bruteforce --count 10
# Escenarios: normal, bruteforce, portscan, beacon, dns_dga, dns_normal, vpn_flapping
# bruteforce/portscan/beacon/dns_dga fijan una IP atacante por lote para que /events/correlate los agrupe
```

Ollama no es servicio ni está en autorun: verificar con `curl http://localhost:11434/api/tags` o levantarlo con `scripts/ensure_ollama.bat`. Urls: dashboard `:8501`, API `:8000/docs`.

## Entorno

- **Windows** es la plataforma real. No dar instrucciones con sintaxis bash (`export`, `&&` en cmd.exe).
- **Python 3.11/3.12 únicamente** — 3.14 rompe SQLModel/Pydantic (PEP 649). No parchear código para 3.14; fijar la versión del venv (consistente con `python:3.11-slim` del Dockerfile).
- `.env` está gitignoreado. `backend/.env` (`OLLAMA_HOST`, `OLLAMA_MODEL`, `DB_PATH`, `SYSLOG_PORT`) se carga automáticamente; `frontend/.env` (`BACKEND_URL`) se lee en `dashboard.py`.
- **Docker (despliegue, solo para el entregable del curso):** este equipo no tiene Docker instalado, así que el despliegue se valida por inspección, no en runtime. Prerequisitos de `docker compose up`: (1) Ollama bindeado a `0.0.0.0:11434`, no solo `127.0.0.1` — el contenedor lo alcanza vía `host.docker.internal`; (2) el backend de la Opción A detenido, o falla por puertos `8000`/`5514` compartidos. Hay `.dockerignore` en backend/ y frontend/ (excluye `.venv` ~400MB del contexto de build) y healthcheck del backend en el compose.
- Lint: config de ruff en `pyproject.toml` (line-length 110; DTZ003/DTZ005 ignorados por decisión documentada — datetimes naive UTC). Ruff está en el venv pero ya no está en `requirements.txt`. No hay typecheck configurado. No inventar comandos de lint.
- **Dependencias**: `plotly` solo en `frontend/requirements.txt` (gráficos interactivos offline). NO está en `backend/requirements.txt`.

## Testing

- Los tests usan un DB temporal en `%TEMP%\ai_noc_test.db`. **El archivo se borra automáticamente al inicio de la sesión de tests** (ver `test_api.py` líneas 13-20) -- si aun así ves conteos de grupos inesperados en `correlate`/`beaconing`/`dns`, revisa si algo más está escribiendo a esa ruta antes de sospechar del código.
- **Tests deben correrse desde `backend/`** porque importan `app.main`.
- Los warnings de `datetime.utcnow()` deprecado son ruido preexistente, no arreglar.

## Convenciones y archivos raros

- Commits: prefijos `feat:`/`fix:`/`docs:`/`test:`/`chore:`/`wip:`, una idea por commit, en español. `git tag vMAJOR.MINOR.PATCH` solo al cerrar una fase del ROADMAP.
- Después de cualquier cambio: correr `pytest tests -v` (todo en verde), actualizar `SPEC.md`/`ROADMAP.md` si el cambio afecta arquitectura o cierra un ítem. **Proponer** un mensaje de commit -- no commitear ni hacer push por cuenta propia, eso lo decide el humano.
