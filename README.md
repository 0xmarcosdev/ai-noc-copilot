# AI-NOC Copilot

Prototipo local de un copiloto de IA para administración de red: recibe
logs de pfSense por syslog, los guarda, y usa un LLM local (Ollama) para
explicar cada evento en lenguaje natural — sin salir nunca de la red
corporativa (diseñado para entornos air-gapped).

> Proyecto final — curso "IA Estratégica: El Programador Aumentado".
> Validado contra un pfSense real de laboratorio (Proxmox). Diseñado para
> escalar a arquitectura multi-sucursal (ver [Roadmap](#roadmap)).

## Arquitectura

```
pfSense (syslog UDP) ──▶ backend/syslog_listener.py ──▶ SQLite
                                                            │
                                              GET /events   │  POST /events/{id}/analyze
                                                            ▼
                                                  Ollama (llama3.2:3b)
                                                            │
                                                            ▼
                                              Streamlit dashboard (chat + eventos)
```

- **backend/**: FastAPI. Escucha syslog en UDP, expone API REST, llama a Ollama.
- **frontend/**: Streamlit. Lista de eventos + botón "Explicar con IA".
- **docker-compose.yml**: levanta los tres servicios (Ollama, backend, frontend).

### Datos de prueba (sin pfSense real disponible)

```bash
python scripts/generate_fake_logs.py --count 15
```

Envía logs sintéticos con formato aproximado de pfSense al listener local.
Útil para desarrollar y probar el pipeline completo sin depender de un
pfSense de laboratorio o de producción. El formato exacto de `filterlog`
está pendiente de verificación contra la wiki oficial (ver `docs/`).

## Cómo correrlo

### Opción A — Desarrollo local, sin Docker (recomendado para iterar rápido)

Requiere que Ollama ya esté corriendo nativo en tu equipo con el modelo descargado
(`ollama list` para confirmar el tag exacto).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=qwen2.5:3b-instruct   # ajusta al tag real de `ollama list`
export DB_PATH=./data/events.db
export SYSLOG_PORT=5514
uvicorn app.main:app --reload
```

En otra terminal:
```bash
cd frontend
pip install streamlit httpx
export BACKEND_URL=http://localhost:8000
streamlit run dashboard.py
```

### Opción B — Docker (para el entregable de despliegue del curso)

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve   # Ollama debe escuchar en todas las interfaces
docker compose up -d
```

En ambos casos:
- Dashboard: http://localhost:8501
- API docs (Swagger): http://localhost:8000/docs
- Configurar pfSense: *Status > System Logs > Settings > Remote Log Servers*
  → apuntar a `<IP de tu equipo>:5514` (UDP).

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest tests -v
```

## Roadmap (fuera del alcance del MVP)

- Multi-sucursal: múltiples fuentes de syslog etiquetadas por sede.
- RAG sobre documentación interna (runbooks, políticas de firewall).
- Detección de anomalías con ML (Isolation Forest) sobre métricas de tráfico.
- Salud técnica de PCs vía agente ligero.
- Escaneo de vulnerabilidades (OpenVAS) con priorización asistida por IA.

## Uso de asistentes de IA en el desarrollo

Este proyecto fue diseñado y construido con asistencia de herramientas de
IA en distintas etapas (arquitectura, scaffolding de código, testing,
documentación). Ver `docs/ai-assisted-development.md` para el detalle de
qué se usó en cada etapa y las transcripciones/capturas de las sesiones
relevantes.
