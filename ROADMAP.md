# ROADMAP — AI-NOC Copilot

> Este documento responde a "¿dónde estoy y qué sigue?". Si te reincorporas
> al proyecto después de unos días y no recuerdas el estado, empieza aquí:
> mira la última casilla marcada, esa es tu punto de partida.
>
> No confundir con `DEVLOG.md` (diario de lo que ya pasó, sesión por sesión)
> ni con `SPEC.md` (arquitectura y decisiones, la fuente de verdad técnica).
> Este archivo es el checklist operativo.

## Cómo marcar el avance

Cambia `- [ ]` por `- [x]` a medida que completas cada punto. Cuando **todas**
las casillas de una fase estén marcadas, esa fase queda "cerrada": commitea,
etiqueta la versión correspondiente (ver convención abajo), y pasa a la
siguiente fase.

---

## Fase 0 — Diseño y alcance ✅ COMPLETA

- [x] Evaluar propuestas de arquitectura, descartar sobrealcance (Elastic,
      Suricata/Zeek completo, multi-sucursal real, modelos 7B+)
- [x] Definir MVP en `SPEC.md`
- [x] Esqueleto del repo (FastAPI + SQLModel + SQLite + Streamlit + Ollama nativo)

## Fase 1 — Ingesta y pipeline base ✅ COMPLETA

- [x] Listener syslog UDP (`syslog_listener.py`)
- [x] Modelo `NetworkEvent` + SQLite
- [x] Endpoints `/health`, `/events`
- [x] Tests iniciales (pytest 4/4)
- [x] Fix: SQLite no creaba la carpeta `data/`
- [x] `.env` + `python-dotenv` (sin export/set manual en Windows)
- [x] Fix: venv fijado a Python 3.11/3.12 (incompatibilidad 3.14 + SQLModel)

## Fase 2 — LLM local ✅ COMPLETA

- [x] `llm_service.py` + prompt `threat_explainer.txt`
- [x] Endpoint `POST /events/{id}/analyze`
- [x] Modelo confirmado: `my-qwen-3b:latest`
- [x] Fix: httpx keep-alive causaba "Server disconnected"
- [x] Pipeline validado end-to-end contra Ollama real

## Fase 3 — Datos sintéticos y verificación de formato ✅ COMPLETA

- [x] `scripts/generate_fake_logs.py` (escenarios: normal, bruteforce, portscan)
- [x] Formato filterlog verificado contra fuente oficial (Perplexity + BNF de
      Netgate + código fuente `pfsense/pfsense` en GitHub)
- [x] `docs/pfsense-filterlog-format.md`

## Fase 4 — Correlación de eventos ✅ COMPLETA

- [x] Detectada la limitación: evento aislado de fuerza bruta = severity "low"
- [x] Regex de extracción de IP atacante desde `raw_message` (validado)
- [x] Endpoint `POST /events/correlate`
- [x] `/summary` extendido con `top_high_severity_types`
- [x] **Probar**: grupo de 10 eventos bruteforce → confirmar `severity: high`
- [x] Tests para `/events/correlate`

## Fase 5.5 — Detección extendida ✅ COMPLETA

- [x] Heurística de entropía (DGA / túneles DNS) -- dns_heuristics.py
- [x] Ingesta de logs DNS (Unbound + dnsmasq) -- dns_parsing.py, formato verificado con Perplexity
- [x] POST /events/detect-beaconing -- coeficiente de variación de intervalos
- [x] POST /events/detect-suspicious-dns
- [x] 3 escenarios sintéticos nuevos: beacon, dns_dga, dns_normal, vpn_flapping
- [x] AGENTS.md fusionado (Claude + OpenCode), linter limpio, bug de contaminación de tests corregido

## Fase 5.6 — Ingesta manual de logs 🔶 EN PROGRESO

- [x] POST /events/ingest (pegar/subir líneas como eventos sin analizar) -- materializa la vía segura de SPEC §8
- [x] UI del dashboard: expander "Ingesta manual" (text_area + file_uploader + botón)
- [x] Tests de ingesta (creación, líneas vacías/CRLF, 422, integración con /correlate)
- [ ] Probar end-to-end con un lote real exportado de la GUI de pfSense (sanitizado)

## Fase 5.7 — Búsqueda, filtros y paginación ✅ COMPLETA

- [x] GET /events paginado (limit/offset) y filtros q / severity / event_type / only_unanalyzed -> {total, limit, offset, items}
- [x] Dashboard: filtros + paginación con session_state (ya no asume respuesta como lista)
- [x] Tests de listado y paginación/filtros
- [x] Probar filtros/paginación en vivo contra el backend con datos reales

## Fase 5.8 — Persistencia y clasificación de correlación ✅ COMPLETA

[#fase-58--persistencia-y-clasificación-de-correlación--en-progreso](#fase-58--persistencia-y-clasificación-de-correlación--en-progreso)

> Corresponde a la "Fase C" del plan de mejoras de dashboard
> (`docs/ai-sessions/Resumen de builds — Fases A y B del dashboard-opencode.md`):
> resuelve las recomendaciones #5 (persistir el histórico de correlación,
> que hoy se pierde al recargar la página) y #6 (distinguir fuerza bruta
> de escaneo de puertos, que antes siempre daba el mismo diagnóstico).

- [x] Columna `correlation_group` en `NetworkEvent` (sin tabla nueva —
decisión consciente para no complicar el esquema SQLite)
- [x] Heurística determinista `classify_port_pattern` en `main.py`: ratio
de puertos destino distintos → `fuerza_bruta` / `escaneo_puertos` /
`None` (indeterminado con pocos eventos o patrón mixto)
- [x] `POST /events/correlate` asigna `correlation_group` a cada evento
del grupo y pasa el patrón detectado como contexto explícito al LLM
- [x] `GET /events/correlation-history` (ya existía como stub, ahora
funcional: agrupa por `correlation_group`, expone IPs, puertos únicos,
patrón, severidad y ventana temporal)
- [x] Tests: `classify_port_pattern` (fuerza bruta / escaneo / ambiguo),
asignación de `correlation_group`, historial agrupado — 29/29 en verde,
ruff limpio
- [x] Sección/botón en el dashboard de Streamlit para consumir
`/events/correlation-history` (el botón actual solo corre `/correlate` al
vuelo; el histórico no es visible tras recargar la página — **esto es lo
que falta para cerrar la fase**)
- [ ] Migración real de esquema (`ALTER TABLE` si la columna no existe)
en vez de depender de recrear la base — ver limitación documentada en
`SPEC.md` §7 — **pendiente para futuro post-entrega, no bloquea la demo**

## Fase 5.9 — Estadísticas y gráficos ✅ COMPLETA

[#fase-59--estadísticas-y-gráficos--completa](#fase-59--estadísticas-y-gráficos--completa)

> "Fase D" del plan de mejoras de dashboard. Resuelve la recomendación
> #10 (panel de estadísticas más rico, gráficos interactivos, exportar) y
> #12 (reporte on-demand sobre un paquete de logs ingerido o filtrado).

- [x] Panel de estadísticas enriquecido (más allá de `by_severity` /
  `top_high_severity_types`): series por tiempo, distribución por tipo de
  evento, eventos correlacionados vs individuales
- [x] Gráficos interactivos con plotly (offline, sin CDN — instalado via
  pip, 100% funcional sin red. Documentado en SPEC §5)
- [x] Exportar datos (CSV/JSON) desde el dashboard — filtros activos
- [x] Botón de reporte on-demand: genera un resumen determinista
  (agregaciones/estadísticas) sobre los eventos filtrados o el último lote
  ingerido (sin pasar por LLM — decision documentada en SPEC §5)
- [x] Tests para endpoint /summary extendido (31/31 en verde, ruff limpio)

## Fase 5.10 — Chat interactivo con el LLM ⬜ PENDIENTE (UI)

> Chat interactivo sobre eventos individuales: el usuario selecciona un
> evento y puede preguntarle al copiloto en lenguaje natural. Backend
> completado (endpoint, streaming, tests); la UI del dashboard queda
> pendiente de decisión del humano (ver preguntas en PARTB-QUESTIONS).

- [x] `chat_service.py`: async generator que llama a Ollama `/api/chat`
  con `stream=true`, reutiliza `_ollama_client_kwargs()` y `keep_alive=10m`
- [x] Endpoint `POST /events/{event_id}/chat`: recibe `{message, history}`,
  arma system prompt con contexto real del evento (raw_message, análisis
  previo si existe, info de correlación si pertenece a un grupo),
  devuelve `StreamingResponse`
- [x] Validación pre-stream: lee el primer chunk antes de enviar el
  status 200 para poder devolver502 limpio si Ollama falla
- [x] Tests: 404 evento inexistente, contexto en system prompt, usa
  `/api/chat` (no `/api/generate`), propagación de error 502
- [x] pytest 37/37, ruff limpio
- [x] UI del dashboard (tabs Eventos / Chat / Correlación, tema claro-oscuro,
      filtros por radio, chat con área scrolleable, lookup de evento vía listado)
- [x] GET /events/{event_id} (hoy el chat depende del listado con id_from/id_to)
- [x] UX mejorada: `selectbox` dinámico para selección de grupos de correlación (elimina adivinación de IDs).
- [x] Fix aplicado: `st.rerun()` post-correlación para actualización inmediata del histórico.
- [x] Estética: CSS personalizado con frame de chat scrolleable, tipografía jerárquica y badges semán
- [ ] Chat sobre grupo de correlación sin reutilizar el event_id como PK

## Fase 6 — Documentación y entrega ⬜ PENDIENTE

- [x] README final revisado (instrucciones probadas de cero, sin asumir nada)
- [x] `SPEC.md` actualizado como última pasada antes de entregar
- [ ] Evidencia de uso de IA: capturas o transcripciones de sesiones clave
      (esta conversación + DeepSeek + Perplexity ya califican, solo hay que
      exportarlas) — **requiere intervención del humano**
- [ ] `docker compose up` probado de punta a punta (Opción B del README) —
      **requiere Docker instalado + Ollama bindeado a 0.0.0.0:11434** —
      verificar prerequisitos en `docs/docker-validation.md`
- [ ] Grabación de demo: ataque simulado → detección → explicación → correlación
      — **guion listo en `docs/demo-script.md`** — requiere humano para grabar
- [ ] Ensayo de la presentación en voz alta, cronometrado — **depende del humano**

---

## Convención de versiones

Formato: **`vMAJOR.MINOR.PATCH — "Nombre descriptivo"`**

- **MAJOR** se queda en `0` hasta que el proyecto sea un MVP demostrable
  completo. Pasa a `1.0.0` cuando termines la Fase 6.
- **MINOR** sube con cada fase cerrada (feature nueva y funcional).
- **PATCH** sube con fixes dentro de una fase ya cerrada (bugs, no features).

| Versión | Nombre | Fase | Estado |
| --- | --- | --- | --- |
| v0.1.0 | Esqueleto funcional | Fase 0-1 | ✅ hecho |
| v0.2.0 | Pipeline validado con Ollama real | Fase 2 | ✅ hecho |
| v0.3.0 | Generador de logs con formato verificado | Fase 3 | ✅ hecho |
| v0.4.0 | Correlación de eventos | Fase 4 | ✅ hecho |
| v0.4.1 | Persistencia y clasificación de correlación | Fase 5.8 | ✅ hecho |
| v0.5.0 | Dashboard completo y Chat interactivo | Fase 5.10 | ✅ hecho |
| **v1.0.0** | **MVP listo para entrega — 4 sept 2026** | Fase 6 | ⬜ pendiente |

### Cómo etiquetar en git

Cuando cierres una fase:

```cmd
git add .
git commit -m "feat: correlacion de eventos por patron de fuerza bruta"
git tag -a v0.4.0 -m "Correlacion de eventos"
git push origin main --tags
```

### Cuándo commitear (no solo cuándo etiquetar)

No esperes a cerrar una fase completa para commitear — eso es exactamente lo
que el curso pide evitar ("historial que refleje el proceso, no solo el
resultado final"). Regla simple:

- **Commitea cada vez que algo funciona y representa una sola idea completa**
  (ej. "arreglé el bug de la carpeta data", "agregué el endpoint de
  correlación") — no acumules 5 cambios distintos en un commit.
- **Prefijo del mensaje** (convención estándar, fácil de aprender):
  `feat:` (funcionalidad nueva), `fix:` (corrección de bug), `docs:`
  (documentación), `test:` (tests), `chore:` (config, dependencias).
- **Al cerrar sesión de trabajo**: commitea aunque quede algo a medias --
  mejor un commit `wip: correlacion de eventos (falta probar con Ollama)`
  que perder el punto de retomar mañana.
- **Etiqueta de versión (`git tag`)**: solo al cerrar una fase completa de
  este ROADMAP, no en cada commit.
  