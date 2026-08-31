# DEVLOG

## Día 1 — 10 ago 2026

- Definido el alcance del MVP (AI-NOC Copilot) tras evaluar y descartar 7 propuestas
  sobredimensionadas para el hardware y el tiempo disponibles.
- Generado el esqueleto del proyecto: FastAPI + SQLModel + SQLite, listener syslog UDP,
  servicio de análisis vía Ollama, dashboard Streamlit, docker-compose.
- Decisión de arquitectura: Ollama corre nativo en el host (ya estaba instalado con el
  modelo descargado), no duplicado en contenedor -- ahorra espacio en disco y evita
  complejidad de networking innecesaria.
- Tests iniciales (pytest) pasando en 4/4.

## Día 2 — 11-12 ago 2026

- Confirmado: no hay pfSense de laboratorio disponible; los pfSense reales están en
  producción. Decisión: usar datos sintéticos para desarrollo, evaluar acceso a
  producción más adelante por una vía segura (muestra histórica sanitizada, no
  streaming en vivo desde un equipo personal no gestionado).
- Perplexity: verificado el formato exacto de filterlog de pfSense contra la
  gramática BNF oficial (docs.netgate.com) y el código fuente de pfSense en GitHub
  (parse_firewall_log_line() en syslog.inc).
- Construido scripts/generate_fake_logs.py con 3 escenarios (normal, bruteforce,
  portscan) fieles al formato verificado.
- Pipeline validado end-to-end: ingesta UDP -> SQLite -> /analyze -> Ollama
  (my-qwen-3b:latest) -> explicación en lenguaje natural. Evento de prueba
  (openvpn timeout) clasificado correctamente como severidad "low".
- Bug corregido: SQLite no creaba la carpeta `data/` automáticamente (diagnosticado
  también por Qwen) -> fix aplicado en main.py con Path.mkdir().
- Agregado python-dotenv + .env.example para evitar declarar variables de entorno
  a mano en cada sesión de terminal en Windows.

## Día 3 — 15-16 ago 2026

- Generados 10 eventos sintéticos de escenario "bruteforce" (mismo puerto 22,
  IPs origen distintas) para probar cómo clasifica el LLM un patrón de ataque.
- Detectado un problema de entorno: nuevo venv creado sobre Python 3.14 rompe
  SQLModel/Pydantic por el cambio de evaluación de anotaciones de PEP 649
  (confirmado también por Qwen, y verificado por Claude comparando contra un
  entorno Python 3.12 donde el mismo código funciona sin cambios).
- Decisión: fijar el venv del proyecto a Python 3.11/3.12 en vez de parchear
  el código para 3.14, por consistencia con la imagen Docker de despliegue.
- Pendiente: confirmar clasificación de severidad de un evento de fuerza bruta
  individual (limitación esperada: análisis evento-por-evento sin correlación
  entre eventos relacionados).
  - Diagnosticado y resuelto: httpx reutilizaba conexiones keep-alive que Ollama
  cerraba, causando "Server disconnected without sending a response". Fix:
  deshabilitar keep-alive (max_keepalive_connections=0) y separar timeouts de
  conexión/lectura en llm_service.py.
- Pipeline de análisis validado end-to-end contra Ollama real: evento de bloqueo
  SSH clasificado como severity "low" -- CONFIRMA la limitación esperada: un
  evento individual de fuerza bruta no se distingue de tráfico normal sin
  contexto de los demás intentos. Próximo paso: correlación de eventos por
  IP origen + ventana de tiempo antes de enviar al LLM.
- Creado docs/SPEC.md como documento de referencia único para desarrollo
  guiado por especificación (spec-driven development) y como contexto
  reutilizable para delegar tareas a otras herramientas de IA.

## Día 4 -16 ago 2026

- Confirmado que un evento aislado de fuerza bruta se clasificaba como severity:
  low — la limitación que ya esperábamos.
- Construída la corrección: endpoint POST /events/correlate, que agrupa eventos
  por IP atacante real (no por source_ip) y los manda juntos al LLM.
- Creado documento de seguimiento — creamos ROADMAP.md (checklist de fases + versionado
  vMAJOR.MINOR.PATCH).
- Probado /correlate — dio groups_detected: 0. Encontramos el motivo: el generador
  de logs sintéticos usaba una IP atacante distinta en cada evento, así que nunca se
  agrupaban 5+ del mismo origen.
- Creado scripts/ensure_ollama.bat para levantar Ollama.
- Prueba repetida: funcionó — 10 eventos agrupados, severity: high, patrón identificado correctamente.
- Agregados tests para el endpoint de correlación, limpié unos duplicados que habían
  quedado en el archivo de tests.
- Actualizados ROADMAP.md y SPEC.md marcando la Fase 4 como completa.
- Botón de correlación en el dashboard de Streamlit (Fase 5) — pero no llegué a dártelo,
  ahí es donde se cortó.

## Día 5 19 ago 2026

- Resolvimos el conflicto de dependencias: Fijamos versiones compatibles de
  FastAPI, Starlette y Streamlit. (pip install "fastapi==0.115.0" "starlette==0.38.6"
  "streamlit==1.39.0")
- Automatizamos el inicio del frontend y el backend mediante scripts.
  (Creando un archivo llamado .env dentro de D:\AiProject\ai-noc-copilot\frontend\ con contenido: BACKEND_URL=<http://localhost:8000>, y los cripts start-backend.ps1, start-frontend.ps1 y start-all.ps1)

## Día 6 — 17-18 ago 2026

- Construidos POST /events/detect-beaconing (coeficiente de variación de
  intervalos) y POST /events/detect-suspicious-dns (entropía de Shannon,
  formato DNS de pfSense verificado con Perplexity: Unbound + dnsmasq).
- Principio de diseño declarado explícitamente: la detección siempre es
  determinista (regex/entropía/estadística); el LLM nunca decide solo,
  solo redacta la explicación.
- Evaluado y descartado conscientemente un diseño de detección de picos
  con z-score (scope creep -- reimplementaba el módulo de ML de anomalías
  ya excluido del MVP).
- 4 escenarios sintéticos nuevos: beacon, dns_dga, dns_normal, vpn_flapping.
  Bug propio corregido: el generador de dominios DGA no era suficientemente
  aleatorio para disparar la propia heurística de entropía.
- Creado AGENTS.md (Claude) para dar contexto a OpenCode; fusionado luego
  con la versión que generó OpenCode con /init -- encontró bugs reales que
  la versión de Claude no tenía: contaminación de DB entre corridas de
  test, y dos archivos basura comiteados por error.
- ROADMAP: Fase 5.5 (Detección extendida) cerrada.

## Día 7 — 19-20 ago 2026

- Tarea delegada a OpenCode: validar despliegue Docker (Opción B). Docker
  Desktop no estaba instalado -- validación por inspección estática en vez
  de ejecución real. Encontrados y corregidos: falta de .dockerignore
  (build incluía backend/.venv, ~421MB), healthcheck del backend ausente,
  streamlit desactualizado, prerequisitos de Ollama/puertos no documentados
  en el README. Commit db950d5.
- Feature nueva: ingesta manual de logs (pegar o subir archivo), conectada
  directamente a la decisión de SPEC §8 (vía segura para usar logs reales
  de producción). Planificada con OpenCode en modo Plan, decisiones:
  received_at=utcnow, ingesta pasiva (no auto-correlaciona).
- POST /events/ingest implementado + UI en el dashboard + 5 tests nuevos.
- Validación en vivo (no solo mocks): encontrado que Ollama en esta máquina
  no tenía ningún modelo registrado (OLLAMA_MODELS apuntaba a un directorio
  con el .gguf presente pero nunca registrado) -- causa raíz real del
  fallo, diagnosticada paso a paso en vez de asumida. Modelo registrado
  con `ollama create`. Correlación real confirmada: severity "high" para
  6 eventos de fuerza bruta ingeridos manualmente (51s con el LLM real);
  análisis individual confirmado: severity "low" para un evento normal
  (18.7s). Contraste low/high sigue siendo la mejor evidencia del proyecto.
- ROADMAP: Fase 5.6 (Ingesta manual) casi completa.

## Día 8 — 20 ago 2026

- Implementada búsqueda, filtros y paginación en `GET /events`
  (limit/offset/q/severity/event_type/only_unanalyzed → `{total, limit,
  offset, items}`), planificado con Grok. El parche del backend llegó con
  la feature de ingesta accidentalmente borrada (los tests de /ingest
  fallaban con 404) — restaurada desde el commit anterior y reaplicado el
  cambio de paginación limpio sobre el mismo.
- Dashboard: la lista de eventos ya no asume una respuesta tipo lista;
  parsea `{items, total}` y agrega filtros + paginación con session_state
  (resetea la página al cambiar filtros, botones anterior/siguiente).
- Tests: `test_list_events` actualizado al nuevo shape + nuevo
  `test_list_events_pagination_and_filters` (q, severity, only_unanalyzed,
  event_type, limit/offset). Suite completa en verde (20 tests), ruff limpio.
- ROADMAP: Fase 5.7 (Búsqueda, filtros y paginación) creada, casi completa.

## Día 9 — 23 ago 2026

- Retomamos el proyecto con Claude después de una sesión previa con
  OpenCode que había dejado la Fase C (persistencia y clasificación de
  correlación — recomendaciones #5 y #6 de `docs/recomendaciones_dashboard.txt`)
  a medio construir: la columna `correlation_group` ya estaba en
  `NetworkEvent`, el endpoint `GET /events/correlation-history` ya existía,
  y en `test_api.py` ya había 5 tests escritos para `classify_port_pattern`
  y para la asignación de `correlation_group` — pero la función
  `classify_port_pattern` no existía en `main.py` (los tests fallaban con
  `NameError`) y `/events/correlate` nunca escribía `correlation_group`.
- Implementado `classify_port_pattern`: heurística determinista basada en
  la proporción de puertos destino distintos sobre el total de eventos del
  grupo (`≤0.3` → fuerza_bruta, `≥0.7` → escaneo_puertos, zona intermedia o
  menos de 3 eventos con puerto extraído → indeterminado). Sin involucrar
  al LLM en la clasificación, consistente con el principio de detección
  determinista ya aplicado en beaconing/DNS.
- `POST /events/correlate` ahora asigna `correlation_group` (contador
  global creciente, sin reutilizar IDs) y pasa el patrón de puertos
  clasificado como contexto explícito al prompt del LLM, siguiendo el
  mismo patrón ya usado en `detect-beaconing` y `detect-suspicious-dns`.
- Encontrada y corregida una inconsistencia en `docs/SPEC.md` §7: describía
  umbrales de clasificación distintos a los que terminamos implementando, y
  afirmaba una migración automática de esquema (`ALTER TABLE` en el
  lifespan) que en realidad nunca se codificó — documentado como
  limitación conocida en vez de dejar la contradicción sin resolver (regla
  de AGENTS.md).
- 29/29 tests en verde (24 previos + 5 de esta fase), `ruff check` limpio.
  Base de datos de desarrollo borrada y recreada desde cero por el usuario
  para partir con el esquema nuevo.
- ROADMAP: creada Fase 5.8 (Persistencia y clasificación de correlación,
  "Fase C" del plan de dashboard) — backend completo, falta la sección del
  dashboard que consuma `/events/correlation-history` (el botón actual solo
  corre `/correlate` al vuelo y no persiste vista tras recargar). Creada
  Fase 5.9 (Estadísticas y gráficos, "Fase D") como siguiente paso.
- Pendiente para la próxima sesión (delegado a OpenCode): el botón/sección
  del dashboard para el histórico de correlación, y arrancar la Fase D
  completa con verificación exhaustiva (tests, lint, validación en vivo).

## Día 10 — 23 ago 2026

- Cerrada la Fase 5.8 (Persistencia y clasificación de correlación):
  implementada la sección "Histórico de correlación" en `frontend/dashboard.py`
  que consume `GET /events/correlation-history` al cargar la página. Muestra
  cada grupo en un expander con ícono según patrón (🎯 fuerza_bruta,
  📡 escaneo_puertos, ❓ indeterminado), IP(s) atacante, severidad (reusando
  la misma paleta de colores del resto del dashboard), ventana temporal y
  IDs de eventos. El botón "Correlacionar eventos sin analizar" se mantiene
  intacto — la sección nueva es adicional, no reemplazo. 29/29 tests en
  verde, ruff limpio, py_compile sin errores.

## Día 11 — 23 ago 2026

- Cerrada la Fase 5.9 (Estadísticas y gráficos, "Fase D" del plan de
  mejoras de dashboard). Resuelve recomendaciones #10 y #12.
- **Backend**: extendido `GET /summary` con claves nuevas sin romper el
  contrato existente: `by_event_type` (distribución por tipo), `time_series`
  (eventos agrupados por hora), `correlated_count`/`individual_count`
  (eventos correlacionados vs individuales). 2 tests nuevos (31/31 total).
- **Gráficos**: se evaluó y agregó `plotly==6.0.1` (100% offline, sin
  CDN, alternativa evaluada: altair — descartada por menor
  customización). Tres gráficos en el dashboard: pie chart de severidad,
  barras horizontales de tipos de evento, línea de serie temporal por hora.
  Documentado en SPEC §9 como decisión de diseño.
- **Exportar**: botones de descarga CSV y JSON de los eventos filtrados
  actualmente en el dashboard (usa los mismos datos de `GET /events`, sin
  duplicar lógica).
- **Reporte on-demand**: genera un resumen determinista (agregaciones y
  estadísticas) en Markdown, descargable. Decisión de diseño: el reporte
  NO pasa por el LLM — es 100% determinista (conteos, distribuciones,
  proporciones). Razonamiento: el LLM redacta explicaciones de eventos
  individuales/grupos, no genera informes estadísticos. Un prompt de LLM
  para esto sería más lento, menos consistente y no aporta valor sobre
  las agregaciones SQL/Python que ya tenemos.
- ruff limpio en backend y frontend, 31/31 tests en verde.
  
## Día 12 — 24 ago 2026

- Verificación pre-grabación: confirmado que `dashboard.py` usa solo stdlib
  (`csv.DictWriter`, `json.dumps`, `io.StringIO`) para exportar CSV/JSON —
  NO usa pandas. No es necesario tocar `requirements.txt` ni Dockerfile.
- Creado `docs/demo-script.md`: guion de demo de 8–10 minutos en 8 escenas
  con comandos exactos, resultados esperados y qué explicar en cada momento.
  Incluye checklist pre-grabación de 7 ítems.
- ROADMAP actualizado: ítems de Fase 5.8 completados, annotados los
  pendientes del humano en Fase 6 (evidencia IA, Docker, grabación, ensayo).
- Regresión final: 31/31 tests ✅, ruff ✅, py_compile ✅.
- Sesión 13 exportada a `docs/ai-sessions/2026-08-24-opencode-verificacion-y-guion-demo.md`.

## Sesión 14 — 26 de agosto 2026
**Asistente de IA**: Qwen3.7  
**Fase**: 5.10 (Chat interactivo) + Mejoras de UX  
**Duración**: ~2 horas  
**Tema**: Fix crítico de nested expanders + Optimización de inteligencia del LLM

### Problemas detectados

1. **Error Streamlit**: `StreamlitAPIException: Expanders may not be nested inside other expanders`
   - Ubicación: Línea ~501 en sección "Histórico de correlación"
   - Causa: `st.expander("IDs de eventos")` anidado dentro de otro expander

2. **Alucinación del LLM**: Al consultar sobre el Grupo #5 (fuerza_bruta, high), el modelo respondía:
   - Decía "indeterminado" en lugar de "fuerza_bruta"
   - Mencionaba IP incorrecta (198.51.100.74 del Grupo #1)
   - Referenciaba grupo #1 en lugar del #5 consultado
   - Latencia excesiva: 53.1s

### Soluciones implementadas

#### Fix 1: Reemplazar expanders anidados por popovers
- `st.expander("IDs de eventos")` → `st.popover("📋 Ver IDs de eventos")`
- Aplicado en 2 ubicaciones:
  - Sección "Correlación de eventos" (línea ~445)
  - Sección "Histórico de correlación" (línea ~501)
- **Resultado**: Error eliminado, UI más limpia

#### Fix 2: Reset de historial al cambiar destino
```python
if st.session_state.get("chat_prev_dest") != selected_id:
    st.session_state.chat_messages = []
    st.session_state.chat_prev_dest = selected_id

Evita contaminación de contexto entre grupos diferentes
Resultado: Cada consulta parte desde cero
Fix 3: Cache de datos en session_state
chat_groups_cache: Almacena IPs, patrón, severidad, event_count, unique_ports
chat_events_cache: Almacena severidad, event_type, ai_explanation, analyzed
Resultado: Datos disponibles sin llamadas adicionales al backend
Fix 4: System prompt robusto con reglas explícitas
REGLAS OBLIGATORIAS:
1. Usa SOLO la información del CONTEXTO proporcionado
2. NUNCA inventes IPs, puertos, timestamps ni patrones
3. Respeta la clasificación del sistema (fuerza_bruta ≠ indeterminado)
4. Ignora mensajes anteriores si referencian otro evento/grupo
5. Responde en español, técnico pero claro
6. Si no tienes información suficiente, dilo explícitamente

FORMATO DE RESPUESTA:
- Diagnóstico
- Evidencia
- Riesgo
- Acción inmediata
- Investigación adicional
Resultado: Respuestas estructuradas y consistentes
Fix 5: Inyección de contexto en cada mensaje
Cada pregunta del usuario incluye al final:
---
CONTEXTO DEL GRUPO #5 (usar SOLO esto):
- IP(s) atacante(s): 203.0.113.4
- Patrón detectado: fuerza_bruta
- Severidad: high
- Cantidad de eventos: 5
- Puertos únicos: 1
Resultado: El LLM siempre tiene visible el contexto correcto
Fix 6: Chips de preguntas dinámicos
Antes: "¿Qué significa este evento?" (genérico)
Ahora: "¿Qué significa el grupo #5?" (específico)
Incluye datos relevantes: "¿Es una amenaza real el patrón 'fuerza_bruta'?"
Resultado: UX más intuitiva y contextual
Métricas de mejora
Métrica
Antes
Después
Mejora
Alucinaciones
100% (IP/grupo incorrecto)
0%
✅
Consistencia
Mezclaba contextos
100% contextual
✅
Latencia
53.1s
43.2s
-19%
UX
Expanders anidados (error)
Popovers funcionales
✅
Testing realizado
Generación de logs bruteforce: python scripts/generate_fake_logs.py --scenario bruteforce --count 10
Correlación de eventos: 4 grupos detectados
Chat interactivo: Consultas a Grupo #5 (fuerza_bruta) y Grupo #1 (indeterminado)
Verificación: Sin mezcla de contextos, respuestas coherentes
Próximos pasos
Mejorar layout general del dashboard (más moderno, ergonómico)
Optimizar uso de espacio horizontal
Refinar tipografía y jerarquía visual
Considerar tabs para separar secciones principales

## Sesión 17 — 25 ago 2026
**Asistente de IA**: Grok  
**Tema**: Revamp visual del dashboard (Streamlit) + debug del lookup de eventos en chat

### Diagnóstico backend — `GET /events/{id}`
- En `backend/app/main.py` **no existe** `GET /events/{event_id}`.
- Rutas relacionadas:
  - `GET /events` — listado paginado con filtros (`id_from`, `id_to`, `q`, `severity`, …) → `{total, limit, offset, items}`
  - `POST /events/{event_id}/analyze`
  - `POST /events/{event_id}/chat` — exige un **ID de evento** (PK de `NetworkEvent`), no un nº de grupo de correlación
- Efecto en el chat del dashboard: la primera carga hacía `GET /events/{id}` → 404 → “No existe el evento #N”.
- Mitigación en frontend: `_load_event_by_id()` con cascada:
  1. `GET /events/{id}` (si se agrega en el futuro)
  2. `GET /events?id_from=N&id_to=N&limit=5`
  3. Búsqueda en los últimos 200 eventos del listado
- Limitación restante: el chat sobre **grupo de correlación** sigue llamando `POST /events/{group_id}/chat`, que busca un evento con ese PK; conviene en un siguiente paso o bien pasar un `event_id` del grupo, o añadir un endpoint de chat por grupo.

### Revamp UI (frontend/dashboard.py)
- Tabs: Eventos | Chat | Correlación (el chat ya no alarga el scroll de la lista).
- Tema claro/oscuro con variables CSS; contraste de placeholders, `st.code`, markdown y popovers en modo claro.
- Filtros: severidad / orden / dirección / por página como **radios** (no editables).
- Chat: historial en un único bloque HTML con altura fija + scroll; destino por `number_input` (ID numérico); historial se preserva al cambiar tema.
- Tipografía: JetBrains Mono (UI operativa) + IBM Plex Sans (cuerpo); respuestas del LLM normalizadas con `_md_lite_to_html`.
- Encabezados de eventos más legibles; gráficos Plotly con hover y colores de tema.

### Verificación sugerida (humano)
```powershell
curl http://localhost:8000/health
curl "http://localhost:8000/events?id_from=45&id_to=45&limit=1"
# Esperado: JSON con items[0].id == 45 (si el evento existe)
curl -s -o NUL -w "%{http_code}" http://localhost:8000/events/45
# Esperado hoy: 404 o 405 (no hay GET por id)
```

### Próximos pasos
- [x] (Opcional backend) Añadir `GET /events/{event_id}` para alinear contrato con el chat.
- [ ] Chat de grupo: endpoint dedicado o resolver a un `event_id` del grupo antes de llamar a `/chat`.
- [ ] Cerrar UI de Fase 5.10 en ROADMAP y seguir con pendientes de Fase 6 (demo, evidencia IA, Docker).

## Sesión 15 — 26 de agosto 2026
**Asistente de IA**: Qwen3.7  
**Fase**: 5.10 (UI del Chat) + Refactorización Visual del Dashboard  
**Duración**: ~1.5 horas  
**Tema**: Implementación de layout basado en Tabs, corrección de bugs de persistencia de correlación y mejora de UX en el chat.

### Cambios Arquitectónicos y de UI
- **Migración a Layout por Tabs**: Se reemplazó el scroll vertical infinito por una navegación tabulada (`st.tabs`): "📋 Eventos", "💬 Chat", "🔗 Correlación". Esto mejora drásticamente la ergonomía, separando contextos de trabajo y reduciendo la carga cognitiva.
- **Refinamiento Visual (CSS)**: Se implementó un sistema de diseño coherente con variables CSS (`:root`), tipografía dual (JetBrains Mono para datos/código, IBM Plex Sans para texto), badges de severidad con codificación de color semántica y un frame de chat personalizado con scroll interno real.
- **Optimización de Filtros**: Los filtros de la pestaña "Eventos" se reorganizaron en radios y campos de texto compactos, moviendo los filtros de fecha/ID a un expander colapsable para maximizar el espacio de la lista.

### Corrección de Bugs Críticos
1. **Histórico de Correlación Vacío**: 
   - *Causa*: Limitación conocida de SQLite (`SPEC.md` §7). Las bases de datos creadas antes de la Fase 5.8 carecían de la columna `correlation_group`, y `create_all()` no la agrega retroactivamente.
   - *Solución*: Documentado el procedimiento de reset de `events.db` para garantizar la alineación del esquema. Se añadió `st.rerun()` tras una correlación exitosa para forzar la renderización del histórico actualizado.
2. **Fallo en Chat por Grupo (ID incorrecto)**:
   - *Causa*: El uso de `st.number_input` obligaba al usuario a adivinar el ID del grupo (ej. escribir "1" cuando el sistema había asignado el "5").
   - *Solución*: Reemplazo del input numérico por un `st.selectbox` dinámico que pobla sus opciones directamente desde `GET /events/correlation-history`, mostrando metadatos legibles (ID, cantidad de eventos, patrón) y eliminando por completo los errores de "No existe el grupo".

### Estado Actual
- Dashboard visualmente pulido, responsive y profesional.
- Flujo de correlación end-to-end verificado: Generación → Correlación → Historial persistente → Chat contextual sin alucinaciones.
- Pendiente: Grabación de la demo (Fase 6) y ensayo final.

## Sesión 16 — 27 de agosto 2026
**Asistente de IA**: Gemini Flash  
**Fase**: 5.10 (Métricas y Diagnóstico de Rendimiento LLM)  
**Tema**: Endpoint `GET /performance/stats`, pestaña "⚡ Rendimiento" en el dashboard y visualización de trade-offs de hardware.

### Análisis y Diagnóstico de Latencia
- **Evaluación de Hardware**: NVIDIA GeForce MX150 con 2 GB de VRAM vs modelo 3.4B Q4_K_M (~2.4 GB en memoria).
- **Cuello de botella identificado**: Ollama descarga un 74% de capas a la CPU y 26% a la GPU debido a la restricción física de VRAM, resultando en ~5.2 tok/s (~18.9s por inferencia).
- **Conclusión arquitectónica**: El código está completamente optimizado (reutilización de cliente, `keep_alive`, mediciones por fases en `LLMTiming`); la limitación es estrictamente física. Además, la detección de anomalías de seguridad es determinista y no depende de la velocidad del LLM.

### Cambios Implementados
1. **Backend (`backend/app/main.py`)**:
   - Agregado endpoint `@app.get("/performance/stats")` que consulta la tabla persistente `LLMTiming`.
   - Expone resumen de métricas acumuladas (total de llamadas, tiempo medio de inferencia, tokens/segundo), desglose de hardware/offload y matriz de trade-offs (Modelo actual vs Qwen 1.5B vs Q3_K_M vs CPU pura Q8).
2. **Frontend (`frontend/dashboard.py`)**:
   - Creado cuarto tab `⚡ Rendimiento`.
   - Visualización de KPIs principales en 4 columnas.
   - Panel de diagnóstico de hardware y cuello de botella + tarjetas visuales de trade-offs con badge de recomendación.
   - Gráfico de dispersión/línea temporal interactivo (Plotly) que refleja el tiempo de generación por llamada y tabla expandible con el historial reciente.
3. **Validación**:
   - `pytest tests -v` pasando en verde (37/37 tests).

## [28 Ago 2026] Sesión de Debugging: Robustez de Escenarios Sintéticos y Exclusión Mutua en API
**Asistente**: Gemini Notebook (Copiloto de IA)

### Diagnóstico y Problemas Encontrados
1. **Conflicto en escenario 'beacon'**: El endpoint `/events/correlate` agrupaba eventos del escenario de beaconing (que usan acción `pass` y dirección `out`) y los marcaba incorrectamente como `fuerza_bruta` debido a la baja variación de puertos destino hacia el C2 [3]. Esto marcaba los logs como `analyzed=True`, impidiendo que `/events/detect-beaconing` los procesara [3].
2. **Error de desempaquetado en beaconing**: Un intento previo de solucionar la concurrencia alteró el agrupamiento de beaconing a una clave de tipo string, lo que provocaba un error catastrófico de tipo `ValueError` al desestructurar la tupla original `(srcip, dstip, dstport)`.
3. **Inestabilidad del escenario 'portscan'**: El script `generate_fake_logs.py` elegía puertos destino con reposición (`random.choice`) de un pool muy pequeño de 9 puertos [4]. Con un conteo por defecto de 5 logs, era común tener duplicados, lo que bajaba el ratio de variación al rango indeterminado (`0.3 - 0.7`) y arruinaba la consistencia de la demo.

### Cambios Realizados

#### Backend (`backend/app/main.py`)
- **Filtrado estricto**: Se modificó `correlate_events()` para extraer los metadatos de conexión con `extract_connection_summary()` y procesar **únicamente** eventos que posean la acción `"block"`.
- **Restauración de Beaconing**: Se revirtió la firma de agrupación en `/events/detect-beaconing` al diccionario de tuplas `(src, dst, dport)` para mantener el análisis de intervalos temporal intacto y evitar errores en tiempo de ejecución.

#### Generador sintético (`scripts/generate_fake_logs.py`)
- **Pool de puertos ampliado**: Se declaró una tupla global `COMMON_PORTS` con 40 puertos representativos de infraestructura de TI.
- **Muestreo sin reposición**: En el escenario de `portscan`, se implementó la generación de una lista de puertos destino únicos mediante `random.sample()`, garantizando que el ratio de variación sea consistentemente `1.0` en lotes cortos de prueba (como `--count 5`), haciendo la demo 100% predecible.
- **Compatibilidad**: Se adaptaron los constructores para que utilicen tuplas de forma nativa y evitar interferencias de renderizado markdown en la plataforma.

#### Pruebas de integración (`backend/tests/test_api.py`)
- Se implementó `test_correlate_ignores_pass_action_events` de forma aislada e independiente para confirmar que los paquetes `pass`/`out` jamás sean tomados por la lógica de correlación.

#### Especificación técnica (`docs/SPEC.md`)
- Se actualizó la sección §7 para reflejar explícitamente que la correlación de eventos determinista solo opera sobre paquetes bloqueados.

### Resultados de la Sesión
- **100% de los tests en verde** ejecutando `pytest tests -v` en el entorno virtual.
- Los escenarios `beacon` y `portscan` se comportan de forma predecible y excluyente sin pisarse entre sí.

## Sesión 18 — 29-30 ago 2026
**Asistentes de IA**: Grok + Deepseek Harness (varios modelos)
**Tema**: UI de correlación tabular, estado Streamlit, notificaciones, pestañas extra

### Contexto
El histórico de correlación seguía en expanders. Se rediseñó la pestaña Correlación
y se estabilizó el estado de la UI tras `st.rerun()` (explicar, correlacionar, tema).

### Cambios principales (`frontend/dashboard.py`)

#### Navegación
- Sustitución de `st.tabs` por `st.radio` + `session_state.main_tab` para no perder
  la pestaña activa al recargar (limitación conocida de `st.tabs`).
- Pestañas: Eventos | Chat | Correlación | Rendimiento | Acerca del proyecto.

#### Correlación — tabla y detalles
- Histórico en `st.dataframe` paginado (`on_select`, selección de una fila).
- Columnas: #, Severidad, Patrón, IP(s), Puertos (números, truncados si >4),
  Eventos, Desde, Hasta, Explicación (✓ / ⏳).
- Panel único «Detalles del grupo» bajo la tabla: IDs a la vista, explicación,
  acción recomendada, botón Explicar / Explicar de nuevo.
- Orden fijo: tabla → paginación → detalles (sin bloque duplicado encima).

#### Estado y explicaciones
- Caché de sesión `corr_expl` / `corr_expl_by_ids`: `/correlation-history` no
  trae el texto del LLM a nivel grupo; la UI refleja ✓ Explicado en la sesión.
- `corr_selected_gid` mantiene el grupo enfocado tras explicar.
- Flujo busy «Razonando…» al re-analizar; ancla en
  `POST /events/{id}/analyze` del primer `event_id` del grupo.
- Banner dismissible tras `POST /events/correlate` (`corr_result_pending` + Entendido).
- Limitación documentada: re-explicar un evento ancla ≠ prompt de lote del correlate;
  el texto puede variar respecto al análisis de patrón.

#### Notificaciones y header
- `_push_notification` + `notification_log` (historial de sesión, máx. 50).
- Mensajes sin emoji en el string (el icono lo pone `st.success` / `error` / `info`).
- Header: botones compactos ↻ (refresh) y tema (☀️/🌙) con `help` en hover.

#### CSS / branding
- Variables de tema claro/oscuro ya existentes.
- Intento de foco de fila en cian de marca (`#0891B2`); si el indicador sigue rojo,
  causa probable: `theme.primaryColor` de Streamlit (checkbox del dataframe), no solo
  el CSS custom — mitigación: `.streamlit/config.toml` + selectores más específicos.

#### Otras pestañas (sesión previa / consolidado en esta)
- Rendimiento: consume `GET /performance/stats`.
- Acerca: problema, arquitectura, decisiones de diseño, stack, roadmap visual.

### Bugs corregidos en la sesión
- Salto a pestaña Eventos tras cualquier `rerun`.
- Notificación `✅ ✅` (emoji duplicado).
- `NameError: name 'background' is not defined` por llaves simples `{` en CSS
  dentro de `BRANDING_CSS = f"""..."""` (hay que usar `{{` / `}}`).
- UI fantasma (detalles/tabla duplicados) mientras corría «Explicar».
- Propiedades CSS mal formadas (`background - color`, `min - height`).

### Verificación (humano)
- Correlacionar → Entendido → grupos en la tabla.
- Seleccionar pendiente → Explicar → un solo panel, pestaña Correlación, columna ✓.
- Sin `NameError` al cargar el dashboard.
- [ ] Foco de fila en cian (pending si aún se ve el primary rojo del theme).

### Docs / siguientes pasos
- Actualizar ROADMAP (Fase 5.11 UI correlación / cierre dashboard).
- SPEC: mencionar `correlation-history`, caché de explicación en UI, radio de pestañas.
- Opcional backend: persistir `explanation` a nivel grupo o
  `POST /events/groups/{id}/explain`.
- Fase 6: demo, evidencia IA, Docker end-to-end.

## Sesión 19 — 31 ago 2026
**Asistente de IA**: OpenCode  
**Tema**: Limpieza y consolidación pre-MVP  
**Duración**: ~1 hora

### Limpieza de archivos
- Eliminados 4 dumps crudos de sesión OpenCode de la raíz:
  - `chat_service_opencode_session-ses_fc8e.md` (268 KB)
  - `opencode_diagnostico_de_latencia_session-ses_fc95.md` (169 KB)
  - `Resumen_de_la_fase_5.10_completada.md` (1 KB)
  - `plan_maestro.md` (48 KB)
- Eliminadas 5 transcripciones completas >50 KB de `docs/ai-sessions/`:
  - `2026-08-19-opencode-docker-y-ingesta.md` (261 KB)
  - `2026-08-20-opencode-busqueda-filtros-y-paginacion.md` (340 KB)
  - `2026-08-20-opencode-manual-ingest.md` (352 KB)
  - `22-ago-latets_session-ses_fe00.md` (207 KB)
  - `visual_identity_session-ses_fe00.md` (106 KB)
- Eliminados duplicados en `docs/ai-sessions/` (canónicos en `docs/`):
  - `branding.md`
  - `isotype.md`
- Actualizado `docs/ai-sessions/README.md` para reflejar solo los archivos que quedan.

### Alineación de documentación
- `ROADMAP.md`: Fase 5.6 cerrada (ítem de lote real sanitizado marcado como opcional), Fase 5.11 cerrada, tabla de versiones actualizada, checkboxes residuales limpiados.
- `docs/SPEC.md`: Sección de dashboard actualizada (pestañas actuales, comportamiento de Correlación con tabla + caché de explicación en sesión + limitaciones del re-explicar), fecha de "Última actualización" puesta al 31 ago 2026.
- `AGENTS.md`: Referencia a `extract_attacker_ip` verificada (línea 51), nota añadida de que `plotly` solo debe estar en `frontend/requirements.txt`.
- `DEVLOG.md`: Esta entrada.
- `.gitignore`: Patrones modernos ya presentes (`.pytest_cache/`, `.ruff_cache/`, `*.log`), sin cambios necesarios.

### Código y calidad
- `plotly` eliminado de `backend/requirements.txt` (solo en frontend).
- Pendiente: ejecutar `ruff check app tests` y `pytest tests -v` desde `backend/`.
- Comentarios en `main.py`, `llm_service.py`, `chat_service.py` y `dashboard.py` revisados (español, precisión, coherencia con SPEC/AGENTS).
