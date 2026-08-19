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

- Confirmado que un evento aislado de fuerza bruta se clasificaba como severity: low — la limitación que ya esperábamos.
- Construída la corrección: endpoint POST /events/correlate, que agrupa eventos por IP atacante real (no por source_ip) y los manda juntos al LLM.
Creado documento de seguimiento — creamos ROADMAP.md (checklist de fases + versionado vMAJOR.MINOR.PATCH).
- Probado /correlate — dio groups_detected: 0. Encontramos el motivo: el generador de logs sintéticos usaba una IP atacante distinta en cada evento, así que nunca se agrupaban 5+ del mismo origen.
- Creado scripts/ensure_ollama.bat para levantar Ollama.
- Prueba repetida: funcionó — 10 eventos agrupados, severity: high, patrón identificado correctamente.
- Agregados tests para el endpoint de correlación, limpié unos duplicados que habían quedado en el archivo de tests.
- Actualizados ROADMAP.md y SPEC.md marcando la Fase 4 como completa.
- Botón de correlación en el dashboard de Streamlit (Fase 5) — pero no llegué a dártelo, ahí es donde se cortó.

## Día 5 19 ago 2026

- Resolvimos el conflicto de dependencias: Fijamos versiones compatibles de FastAPI, Starlette y Streamlit. (pip install "fastapi==0.115.0" "starlette==0.38.6" "streamlit==1.39.0")
- Automatizamos el inicio del frontend y el backend mediante scripts. (Creando un archivo llamado .env dentro de D:\AiProject\ai-noc-copilot\frontend\ con contenido: BACKEND_URL=<http://localhost:8000>, y los cripts start-backend.ps1, start-frontend.ps1 y start-all.ps1)
