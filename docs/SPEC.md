# SPEC — AI-NOC Copilot

> Documento único de referencia del proyecto. Es la fuente de verdad: si el
> código y este documento se contradicen, se actualiza uno de los dos antes
> de seguir — nunca se deja la contradicción sin resolver.
>
> **Para otras IAs**: pega este documento completo al inicio de cualquier
> conversación donde le pidas ayuda a otra herramienta (DeepSeek, Gemini,
> Cursor, etc.) sobre este proyecto. Contiene todo el contexto necesario
> para que la respuesta sea consistente con la arquitectura real, en vez de
> genérica o contradictoria con lo que ya existe.

## 1. Problema y objetivo

Administrador de red de una empresa con arquitectura hub-and-spoke
(sucursales con pfSense → sede central), red **air-gapped** (sin acceso a
Internet). Revisar logs de firewall manualmente es lento y no escala. El
LLM en la nube no es una opción (ni por política, ni por falta de
Internet).

**Objetivo**: un copiloto local que recibe logs de pfSense, los guarda, y
usa un LLM local (Ollama) para explicarlos y clasificarlos en lenguaje
natural — sin salir nunca de la red del usuario.

Proyecto final de curso — entrega 4 sept 2026. Requisitos de la entrega:
control de versiones con historial real, evidencia de uso de asistentes de
IA, documentación (este archivo + README + Swagger), testing, demo.

## 2. Alcance

### Dentro del MVP

- Ingesta de syslog UDP (formato filterlog de pfSense, verificado).
- Almacenamiento en SQLite.
- Análisis de eventos individuales vía LLM local (severidad, tipo, explicación).
- Generación de datos sintéticos para pruebas (no depende de pfSense disponible).
- Dashboard web (Streamlit): Eventos (filtros/paginación), Chat, Correlación (histórico tabular + detalles), Rendimiento, Acerca.
- Correlación: detección determinista + LLM en /events/correlate; la UI puede re-explicar vía evento ancla y caché de sesión hasta que el histórico exponga explanation.(ver §7).

### Fuera de alcance (Roadmap, no se construye ahora)

- Multi-sucursal real / múltiples fuentes de syslog simultáneas.
- RAG sobre documentación interna (runbooks, políticas).
- ML de anomalías (Isolation Forest) sobre métricas de tráfico.
- Salud técnica de PCs, escaneo de vulnerabilidades.
- Cualquier acción automática sobre el firewall (el LLM solo explica y
  recomienda, nunca ejecuta cambios).
- Conexión a pfSense de producción en vivo desde el equipo de desarrollo
  (ver §8, decisión de seguridad).

## 3. Arquitectura

```
pfSense (o generador sintético) --UDP syslog:5514--> syslog_listener.py
                                                            |
                                                            v
                                                    SQLite (NetworkEvent)
                                                            |
                              GET /events   <----+----> POST /events/{id}/analyze
                                                            |
                                                            v
                                              llm_service.py --HTTP--> Ollama
                                                            (my-qwen-3b:latest, nativo en host)
                                                            |
                                                            v
                                              Streamlit dashboard (chat + eventos)
```

**Decisión de diseño clave**: Ollama corre nativo en el host, no en
contenedor — ya estaba instalado con el modelo descargado; duplicarlo
gastaría disco (SSD limitado) y complicaría el networking sin beneficio.
Docker se usa solo para backend + frontend, reservado para el entregable
de despliegue del curso; el desarrollo diario corre en venv sin Docker.

## 4. Modelo de datos

`NetworkEvent` (`backend/app/models.py`):

| Campo | Tipo | Notas |
|---|---|---|
| id | int | PK autoincremental |
| received_at | datetime | timestamp de ingesta |
| source_ip | str? | IP origen del paquete UDP de syslog |
| raw_message | str | línea de log cruda, sin parsear |
| severity | str? | `low` / `medium` / `high`, lo rellena el LLM |
| event_type | str? | lo rellena el LLM |
| ai_explanation | str? | explicación en lenguaje natural |
| analyzed | bool | false hasta que se llama `/analyze` |
| correlation_group | int? | id de grupo de correlación, indexado; `None` hasta que `/events/correlate` lo asigna (ver §7) |

Decisión: el log crudo se guarda tal cual, sin parser dedicado de
filterlog. El LLM interpreta el CSV directamente. Un parser estructurado
(extraer IP/puerto/acción como columnas propias) es la mejora natural
post-MVP si se necesita filtrar/agregar por esos campos sin depender del LLM.

## 5. Contrato de API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | liveness check |
| GET | `/events?limit=&offset=&q=&severity=&event_type=&only_unanalyzed=&id_from=&id_to=&received_at_from=&received_at_to=&sort_by=&sort_dir=` | lista eventos paginados, más recientes primero; responde `{total, limit, offset, items}` |
| POST | `/events/ingest` | ingesta manual: guarda líneas pegadas/subidas como eventos sin analizar (ver §8) |
| POST | `/events/{id}/analyze` | envía el evento al LLM, persiste el resultado |
| POST | `/events/correlate?window_minutes=&threshold=` | agrupa eventos no analizados por IP atacante, clasifica patrón de puertos (fuerza bruta / escaneo), asigna `correlation_group` y envía al LLM |
| GET | `/events/correlation-history?limit=` | historial de grupos de correlación: retorna grupos agrupados por `correlation_group` con metadatos (IPs, patrón, severidad, ventana temporal, IDs) |
| POST | `/events/{event_id}/chat` | chat interactivo sobre un evento: recibe `{message, history}`, devuelve `StreamingResponse` con la respuesta del LLM (streaming puro) |
| GET | `/summary?hours=` | resumen enriquecido: distribución por severidad, tipos dominantes, eventos correlacionados vs individuales, series temporales por hora, distribución por tipo de evento |
| GET | `/performance/stats` | Hardware + latencias (pestaña Rendimiento) |

Swagger autogenerado por FastAPI en `/docs` — es la documentación de API
formal exigida por el curso, no se mantiene a mano.

Errores: `404` si el evento no existe, `422` si el contenido de `/ingest`
está vacío o excede el límite de líneas, `502` si Ollama no responde o
devuelve algo no parseable (nunca `500` silencioso — ver `llm_service.py`).

Filtros de `/events`: `q` (subcadena en `raw_message`), `severity` (igualdad),
`event_type` (subcadena), `only_unanalyzed` (boolean), `id_from`/`id_to`
(rango cerrado de IDs; invertido = resultado vacío, el dashboard lo
intercambia antes de enviarlo), `received_at_from`/`received_at_to`
(ventana de ingesta, datetimes naive UTC). Orden opcional: `sort_by`
(`id` / `received_at` / `severity` / `event_type`, validado con Literal —
valor inválido devuelve 422) y `sort_dir` (`asc`/`desc`); por defecto
`received_at` descendente con `id` como desempate para paginación
determinista. `limit` se acota a [1, 500] y `offset` a >= 0.

## 6. Contrato del LLM (Threat Explainer)

- Modelo: `my-qwen-3b:latest` (Qwen 2.5 3B cuantizado, ~2.1GB), vía Ollama
  nativo, `OLLAMA_HOST=http://localhost:11434`.
- Prompt: `backend/app/prompts/threat_explainer.txt`. Recibe `{log_raw}`,
  exige salida JSON estricta con 4 claves: `severity`, `event_type`,
  `explanation`, `recommended_action`.
- Llamado con `"format": "json"` y `temperature: 0.1` (queremos
  clasificación consistente, no creatividad).
- **No modificar el contrato de salida (las 4 claves) sin actualizar
  también `main.py` donde se consume `result["severity"]`, etc.** — es el
  punto de acoplamiento más frágil del proyecto.

### Chat interactivo (POST /events/{event_id}/chat)

El chat interactivo usa `/api/chat` de Ollama (NO `/api/generate`) con
`stream=true` para devolver la respuesta fragmento a fragmento vía
`StreamingResponse` de FastAPI. El system prompt se arma dinámicamente
con el contexto real del evento (raw_message, análisis previo si existe,
info de correlación si pertenece a un grupo). Las mismas reglas del
`threat_explainer.txt` aplican: nunca inventar IPs, puertos, ni contexto
de red que no esté en los datos reales. `keep_alive=10m` (misma constante
que `_call_ollama` en `llm_service.py`). La latencia del primer chunk es
la misma que para `/api/generate` (~15-38s según si el modelo está
caliente o frío, ver `docs/llm-latency-diagnosis.md`).

## 7. Correlación de eventos

`POST /events/correlate` agrupa eventos no analizados por IP atacante (dentro de una ventana de tiempo configurable). Importante: Este endpoint solo considera eventos cuya acción extraída sea de bloqueo (action == "block"), asegurando que conexiones legítimas o flujos periódicos permitidos (como el tráfico de beaconing) no interfieran ni sean clasificados erróneamente en este análisis.

1. **Clasificación determinista de puertos** (`classify_port_pattern` en
   `main.py`): calcula la proporción de puertos destino *distintos* sobre
   el total de eventos del grupo (usa `extract_connection_summary`, no
   `source_ip`).
   - `< 3` eventos con puerto extraíble → `None` (indeterminado; muestra
     muy chica para clasificar con confianza).
   - proporción de puertos distintos `≤ 0.3` → `fuerza_bruta` (casi todos
     los intentos van al mismo puerto, ej. 5 intentos SSH → 1 puerto de 5).
   - proporción `≥ 0.7` → `escaneo_puertos` (casi todos los puertos son
     distintos, ej. 6 puertos de 6 eventos).
   - zona intermedia (`0.3` – `0.7`) → `None` (patrón mixto, no nos
     animamos a etiquetar).
   Es 100% determinista (sin LLM); los umbrales viven como constantes
   (`MIN_EVENTS_FOR_PORT_PATTERN`, `BRUTEFORCE_MAX_RATIO`,
   `PORTSCAN_MIN_RATIO`) al inicio de `main.py`.
2. **Asignación de `correlation_group`**: todos los eventos del grupo
   reciben el mismo ID de grupo (entero global creciente: se calcula
   `max(correlation_group) + 1` antes de procesar los grupos de la
   llamada, y se incrementa por cada grupo nuevo — nunca se reutiliza un
   ID, aunque haya huecos).
3. **Explicación LLM**: el patrón clasificado (`fuerza_bruta` /
   `escaneo_puertos` / `indeterminado`) se incluye como contexto explícito
   en el prompt de correlación, igual que en `detect-beaconing` y
   `detect-suspicious-dns` — el LLM nunca decide el patrón, solo lo explica.

`GET /events/correlation-history` retorna los grupos más recientes
(ordenados por `correlation_group` descendente) con metadatos: IPs
atacante, puertos únicos, patrón, severidad, ventana temporal
(`first_seen`/`last_seen`) y lista de IDs.

**Limitación conocida (no resuelta aún)**: el campo
`NetworkEvent.correlation_group` se crea vía
`SQLModel.metadata.create_all()` en el `lifespan` de arranque, que **solo
crea tablas nuevas, no agrega columnas a tablas SQLite existentes**. Una
base de datos creada con una versión anterior del modelo (sin esta
columna) no se migra sola — hay que borrar el archivo `.db` y dejar que
se recree, o migrar a mano (`ALTER TABLE networkevent ADD COLUMN
correlation_group INTEGER`). No es un problema en desarrollo (datos
sintéticos, se regeneran fácil) pero sí sería un problema real con datos
de producción — candidato a arreglar antes de la Fase 6 si hay tiempo.

La UI del histórico muestra estado de explicación con caché de sesión del dashboard si el payload de correlation-history no incluye texto del LLM. Re-explicar desde la UI usa el evento ancla del grupo (/events/{id}/analyze); no sustituye el prompt de lote de explain_correlated_events.

## 8. Decisiones de seguridad / datos

- No hay pfSense de laboratorio disponible; los pfSense reales están en
  producción. Decisión: **no** se conecta el equipo de desarrollo (laptop
  personal, no gestionado) a la red de producción para captura de logs en
  vivo. Se usa el generador sintético (`scripts/generate_fake_logs.py`,
  formato verificado contra fuente oficial de pfSense) para todo el
  desarrollo y la demo.
- Si se necesita mayor realismo, la vía aceptada es: exportar manualmente
  un lote pequeño de logs históricos desde la GUI de pfSense (acceso ya
  autorizado del administrador), sanitizar IPs internas si aplica, y
  usarlos como archivo de muestra — nunca streaming continuo en vivo hacia
  un dispositivo no gestionado.
- Esta vía se materializa con `POST /events/ingest` (pegar o subir el lote
  exportado desde el dashboard). Los eventos se marcan como "recién
  recibidos" (`received_at = utcnow`) para que las ventanas de correlación
  funcionen de inmediato sobre el lote; la sanitización de IPs sigue siendo
  un paso manual del operador antes de ingerir.

## 9. Entorno y configuración

Variables de entorno (`backend/.env`, ver `.env.example`):
`OLLAMA_HOST`, `OLLAMA_MODEL`, `DB_PATH`, `SYSLOG_PORT`.

**Restricción de plataforma importante**: el entorno de desarrollo es
Windows. El venv del proyecto debe crearse con **Python 3.11 o 3.12** —
Python 3.14 rompe SQLModel/Pydantic por cambios en evaluación de
anotaciones (PEP 649). No parchear el código para 3.14; fijar la versión
de Python en su lugar (consistente con `python:3.11-slim` del Dockerfile).

**Gráficos interactivos (Fase 5.9)**: se agregó `plotly==6.0.1` al
`requirements.txt` para gráficos interactivos en el dashboard (pie charts,
barras, series temporales). Plotly funciona 100% offline una vez
instalado — no realiza llamadas de red, ni usa CDN, ni descarga assets
en runtime. Es la misma categoría de dependencia que Ollama: se instala
una vez y funciona sin conexión. Alternativa evaluada: `altair` (más
ligero pero menos customizable). Decisión: plotly por la riqueza de
interactividad y soporte nativo en Streamlit (`st.plotly_chart`). Los
archivos `.js` de plotly se sirven desde el paquete pip instalado localmente,
no desde ningún CDN externo.

## 10. Testing

`backend/tests/test_api.py` (pytest): health check, listado de eventos,
404 en evento inexistente, 502 simulando a Ollama caído (mock). Correr con
`pytest tests -v` desde `backend/`.

## 11. Instrucciones para asistentes de IA que trabajen en este repo

- No cambies el contrato de 4 claves del JSON del LLM (§6) sin avisar
  explícitamente que rompe `main.py`.
- No agregues dependencias de servicios en la nube (todo debe funcionar
  air-gapped, es un requisito de diseño, no una preferencia).
- Si proponés un cambio de arquitectura (nueva base de datos, nuevo
  framework, Docker para Ollama, etc.), primero verificá contra §3 si
  contradice una decisión ya tomada — y si la contradice, decilo
  explícitamente en vez de simplemente reemplazarla.
- Windows es la plataforma de desarrollo real — no asumas sintaxis bash
  (`export`, `&&` en cmd.exe) en instrucciones de terminal.
- Este archivo se actualiza junto con cada cambio de arquitectura
  significativo — si hacés un cambio así, proponé también el diff de esta
  sección correspondiente.

---
*Última actualización: 29 ago 2026 — UI correlación tabular, navegación por radio, pestañas rendimiento/acerca.*
