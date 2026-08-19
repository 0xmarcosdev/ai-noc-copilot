# AGENTS.md — AI-NOC Copilot

Copiloto local air-gapped de logs de pfSense (FastAPI + SQLModel/SQLite + Streamlit + Ollama nativo). Proyecto final de curso (entrega 4 sept 2026). **Todo el repo está en español** — documentación, comentarios, prompts y mensajes de commit se escriben en español.

## Punto de partida

- `docs/SPEC.md` — fuente de verdad técnica; `ROADMAP.md` — checklist operativo de fases; `DEVLOG.md` — diario de sesiones. **`SPEC.md` §11 contiene instrucciones explícitas para asistentes de IA** (contrato LLM, no-nube, decisiones de arquitectura); respetarlas.
- El repo corre con el **generador de logs sintéticos**, no con pfSense real (los reales están en producción).

## Arquitectura (gotchas no obvios)

- `backend/app/main.py` es el único entrypoint (`uvicorn app.main:app`). Escucha syslog UDP en `5514` (tarea asíncrona en `syslog_listener.py`).
- **`NetworkEvent.source_ip` NO es la IP del atacante**: es la IP del paquete UDP de syslog (el propio pfSense). Toda correlación extrae la IP real del `raw_message` con regex (`extract_attacker_ip` en `main.py:46`). No cambiar esto a `source_ip`.
- **La detección es determinista, el LLM solo explica** (principio de SPEC): beaconing = coeficiente de variación de intervalos (`main.py`), DGA = entropía de Shannon (`dns_heuristics.py`). El LLM recibe el hallazgo ya detectado y redacta la explicación.
- **Contrato del LLM**: 4 claves JSON estrictas (`severity`, `event_type`, `explanation`, `recommended_action`), prompts en `backend/app/prompts/*.txt`, llamado con `"format": "json"` y `temperature: 0.1`. No cambiar el contrato sin actualizar los consumidores en `main.py` (punto de acoplamiento más frágil).
- **Ollama corre nativo en el host, NO en Docker.** `docker-compose.yml` solo levanta backend+frontend y es solo para el entregable del curso; el desarrollo diario corre con venv. docker-compose usa `qwen2.5:3b-instruct` (stale); el modelo real de desarrollo es `my-qwen-3b:latest` (`.env.example`, SPEC, scripts).

## Comandos

```powershell
# Backend (requiere backend/.env, se carga solo via python-dotenv)
cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
# o: scripts\start-backend.ps1  (frontend: start-frontend.ps1, ambos: start-all.ps1)

# Tests (venv; NO necesita Ollama, el LLM se mockea)
cd backend; .\.venv\Scripts\python.exe -m pytest tests -v

# Logs sintéticos (requiere backend corriendo)
python scripts/generate_fake_logs.py --scenario bruteforce --count 10
# Escenarios: normal, bruteforce, portscan, beacon, dns_dga, dns_normal, vpn_flapping
# bruteforce/portscan/beacon/dns_dga fijan una IP atacante por lote para que /events/correlate los agrupe
```

Ollama no es servicio ni está en autorun: verificar con `curl http://localhost:11434/api/tags` o levantarlo con `scripts/ensure_ollama.bat`. Urls: dashboard `:8501`, API `:8000/docs`.

## Entorno

- **Windows** es la plataforma real (PS1 con rutas hardcodeadas a `D:\AiProject\ai-noc-copilot`). No dar instrucciones con sintaxis bash (`export`, `&&` en cmd.exe).
- **Python 3.11/3.12 únicamente** — 3.14 rompe SQLModel/Pydantic (PEP 649). No parchear código para 3.14; fijar la versión del venv (consistente con `python:3.11-slim` del Dockerfile).
- `.env` está gitignoreado. `backend/.env` (`OLLAMA_HOST`, `OLLAMA_MODEL`, `DB_PATH`, `SYSLOG_PORT`) se carga automáticamente; `frontend/.env` (`BACKEND_URL`) se lee en `dashboard.py`.
- No hay config de lint/typecheck (ruff instalado pero sin config). No inventar comandos de lint.

## Testing

- Los tests usan un DB temporal persistente `%TEMP%\ai_noc_test.db` que **sobrevive entre corridas**; eventos viejos contaminan los tests de correlación/beaconing/DNS (fallan con `groups_detected` inesperado). Si pasa, borrarlo antes de re-correr:
  `Remove-Item "$env:TEMP\ai_noc_test.db"` y reintentar.
- Los warnings de `datetime.utcnow()` deprecado son ruido preexistente, no arreglar.
- Tests corriendo desde `backend/` porque importan `app.main` (los scripts `start-*.ps1` también asumen estar ahí).

## Convenciones y archivos raros

- Commits: prefijos `feat:`/`fix:`/`docs:`/`test:`/`chore:`/`wip:`, una idea por commit, en español. `git tag vMAJOR.MINOR.PATCH` solo al cerrar una fase del ROADMAP.
- Archivos comiteados pero muertos que ignorar: `scripts/Dns heuristics.py` (duplicado con espacio del real `backend/app/dns_heuristics.py`) y `backend/file__memory_` (basura). Editar siempre la copia real en `backend/app/`.