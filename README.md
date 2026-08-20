# AI-NOC Copilot

Prototipo local de un copiloto de IA para administración de red: recibe
logs de pfSense por syslog, los guarda, y usa un LLM local (Ollama) para
explicar cada evento en lenguaje natural y detectar patrones (ej. fuerza
bruta) mediante correlación de eventos — sin salir nunca de la red
corporativa (diseñado para entornos air-gapped).

> Proyecto final — curso "IA Estratégica: El Programador Aumentado".
> No hay pfSense de laboratorio disponible (los pfSense reales están en
> producción); el desarrollo y la demo usan un generador de logs sintéticos
> con formato verificado contra fuentes oficiales de pfSense (ver
> `docs/pfsense-filterlog-format.md`). Diseñado para escalar a arquitectura
> multi-sucursal (ver Roadmap más abajo).

## Documentación del proyecto

Este README es el punto de entrada. El resto de la documentación vive en el repo, no en una Wiki separada:

- **[`docs/SPEC.md`](docs/SPEC.md)** — arquitectura, decisiones de diseño, contratos de API/LLM. La fuente de verdad técnica.
- **[`ROADMAP.md`](ROADMAP.md)** — checklist de fases, qué está hecho y qué sigue, convención de versiones.
- **[`DEVLOG.md`](DEVLOG.md)** — diario de sesiones: qué se hizo, con qué asistente de IA, por qué.
- **[`docs/pfsense-filterlog-format.md`](docs/pfsense-filterlog-format.md)** — formato de log verificado contra fuentes oficiales.

## Arquitectura

```
pfSense (o generador sintético) ──▶ backend/syslog_listener.py ──▶ SQLite
                                                                       │
                          GET /events  │  POST /events/{id}/analyze   │  POST /events/correlate
                                                                       ▼
                                                        Ollama (my-qwen-3b:latest, nativo en el host)
                                                                       │
                                                                       ▼
                                                      Streamlit dashboard (eventos + correlación)
```

- **backend/**: FastAPI. Escucha syslog en UDP, expone API REST, llama a Ollama.
  - `POST /events/{id}/analyze`: explica un evento individual.
  - `POST /events/correlate`: agrupa eventos por IP atacante dentro de una
    ventana de tiempo y evalúa el patrón conjunto (resuelve la limitación de
    que un evento aislado de fuerza bruta se clasifica como severidad baja).
- **frontend/**: Streamlit. Lista de eventos paginada con filtros por texto,
  severidad y tipo, botón "Explicar con IA", y botón "Correlacionar eventos"
  con vista de patrones detectados. Incluye
  un panel de **ingesta manual** (`POST /events/ingest`) para pegar o subir
  un lote de logs — la vía segura de `SPEC.md` §8 para usar logs reales de
  pfSense sin streaming en vivo (sanitizar IPs internas antes de pegar).
- **Ollama**: corre nativo en el host, no en contenedor (ver `SPEC.md` §3
  para la justificación).
- **docker-compose.yml**: levanta backend + frontend (Ollama se conecta
  desde el contenedor al host). Reservado para el entregable de despliegue
  del curso — el desarrollo diario corre sin Docker (ver Opción A abajo).

### Datos de prueba (sin pfSense real disponible)

```bash
python scripts/generate_fake_logs.py --scenario normal --count 15
python scripts/generate_fake_logs.py --scenario bruteforce --count 10
python scripts/generate_fake_logs.py --scenario portscan --count 10
```

Envía logs sintéticos con formato **real y verificado** de `filterlog` de
pfSense al listener local (ver `docs/pfsense-filterlog-format.md` para las
fuentes: gramática BNF oficial + código fuente de pfSense). Los escenarios
`bruteforce` y `portscan` usan una única IP atacante fija por lote, para que
`POST /events/correlate` pueda agruparlos y detectar el patrón.

## Cómo correrlo

### Opción A — Desarrollo local, sin Docker (recomendado para iterar rápido)

Requiere que Ollama ya esté corriendo nativo en tu equipo con el modelo
descargado (`ollama list` para confirmar el tag exacto). Si Ollama no
arranca solo al prender el equipo, usa `scripts/ensure_ollama.bat` (Windows)
para levantarlo sin necesidad de ponerlo en autorun.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env           # en Linux/Mac: cp .env.example .env
uvicorn app.main:app --reload
```

`backend/.env` centraliza `OLLAMA_HOST`, `OLLAMA_MODEL`, `DB_PATH` y
`SYSLOG_PORT` — se carga solo, sin necesidad de `export`/`set` en cada
sesión de terminal.

En otra terminal:
```bash
cd frontend
pip install streamlit httpx
streamlit run dashboard.py
```

### Opción B — Docker (para el entregable de despliegue del curso)

**Pasos previos obligatorios** — sin estos, el contenedor no arranca o no
alcanza a Ollama:

1. **Ollama debe escuchar en todas las interfaces, no solo localhost.** El
   backend del contenedor se conecta vía `host.docker.internal:11434`; si
   Ollama solo bindea `127.0.0.1`, la conexión se rechaza. Verificá que esté
   escuchando en `0.0.0.0`:

   ```powershell
   netstat -ano | findstr 11434   # debe mostrar 0.0.0.0:11434, NO 127.0.0.1:11434
   ```

   Si solo escucha en `127.0.0.1`, reinicialo con:

   ```powershell
   $env:OLLAMA_HOST = "0.0.0.0:11434"; ollama serve
   ```

2. **Detené el backend de la Opción A si está corriendo.** El backend de
   desarrollo y estos contenedores comparten los puertos `8000` y `5514/udp`;
   si ambos corren a la vez, el build falla con `port is already allocated`.

```bash
docker compose up -d --build
```

En ambos casos:
- Dashboard: http://localhost:8501
- API docs (Swagger): http://localhost:8000/docs
- Configurar pfSense real (si se dispone de uno): *Status > System Logs >
  Settings > Remote Log Servers* → apuntar a `<IP de tu equipo>:5514` (UDP).

Verificación rápida de punta a punta (Opción B):

```bash
curl http://localhost:8000/health                    # {"status":"ok"}
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501   # 200
python scripts/generate_fake_logs.py --scenario bruteforce --count 10
# después, en el dashboard: botón "Correlacionar eventos sin analizar"
docker compose ps            # backend "healthy", frontend "running"
docker compose logs -f backend
```

La base de datos vive en el volumen `backend_data` y persiste entre
`docker compose down`/`up`. Para resetear la demo desde cero:
`docker compose down -v` (borra también el volumen y los eventos).

## Testing

```bash
cd backend
pip install -r requirements.txt
pytest tests -v
```

## Roadmap (fuera del alcance del MVP)

Ver `ROADMAP.md` para el checklist completo por fases y la convención de
versiones. Fuera de alcance del MVP del curso:

- Multi-sucursal: múltiples fuentes de syslog etiquetadas por sede.
- RAG sobre documentación interna (runbooks, políticas de firewall).
- Detección de anomalías con ML (Isolation Forest / z-score) sobre métricas de tráfico.
- Salud técnica de PCs vía agente ligero.
- Escaneo de vulnerabilidades (OpenVAS) con priorización asistida por IA.

## Uso de asistentes de IA en el desarrollo

Este proyecto fue diseñado y construido con asistencia de varias
herramientas de IA en distintas etapas: arquitectura y coherencia general
(Claude), debugging puntual (DeepSeek, Qwen), investigación con fuentes
verificables (Perplexity), entre otras. Ver `DEVLOG.md` para el detalle
sesión por sesión de qué se usó para qué, y por qué.
