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
- Dashboard web (Streamlit): lista de eventos + botón "Explicar con IA".
- Correlación básica de eventos relacionados (en progreso — ver §7).

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
| GET | `/summary?hours=` | conteo de eventos analizados por severidad |

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

## 7. Limitación conocida y en desarrollo: correlación

**Confirmado empíricamente (16 ago 2026)**: un evento de bloqueo SSH
aislado se clasifica como `severity: low` — correcto desde la perspectiva
de un solo evento, pero insuficiente cuando en realidad son 10 intentos
seguidos desde distintas IPs al mismo puerto (patrón de fuerza bruta). El
LLM nunca ve los eventos relacionados porque `/analyze` opera sobre un
`id` a la vez.

**Próximo trabajo**: endpoint que agrupe eventos no analizados por
`(dstport, dst_ip)` o por `src_ip` dentro de una ventana de tiempo
(ej. 5-10 min), y si supera un umbral de repeticiones, envíe el lote
completo al LLM en un solo prompt para que evalúe el patrón, no eventos
sueltos.

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
*Última actualización: 21 ago 2026 — Fase B de mejoras de dashboard: /events
acepta filtros por rango de ID y fecha, y ordenación por campo (params
opcionales; contrato previo intacto).*
