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
  