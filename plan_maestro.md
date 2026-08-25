# Plan maestro — Chat interactivo, presentación y producción de la demo
### AI-NOC Copilot — de acá al 4 de septiembre 2026

> Este documento es la fuente de verdad de esta tanda de trabajo. Está pensado
> para pegarse en el repo (`docs/plan-produccion-entrega.md`) y para copiar/pegar
> secciones enteras como prompt a OpenCode. Cada fase tiene: contexto, decisiones
> ya tomadas, lo que queda abierto para que decidas vos, un prompt listo para el
> agente de código, pruebas obligatorias y un commit propuesto.
>
> **Orden recomendado de ejecución:** 0 → 1 → 2 → 6 (Docker, en paralelo si querés)
> → 3 → 4 → 5 → 7. La Fase 0 va primero porque bloquea la Fase 1 — no tiene
> sentido construir un chat en vivo sobre una latencia que todavía no entendés.

---

## Índice

- [Fase 0 — Diagnóstico y optimización de latencia de Ollama](#fase-0)
- [Fase 1 — Chat interactivo en el dashboard (Idea 3)](#fase-1)
- [Fase 2 — Pestaña "Acerca del proyecto" (Idea 1)](#fase-2)
- [Fase 3 — Diagramas estilo pizarra sin saber dibujar (Idea 5)](#fase-3)
- [Fase 4 — Slidev, export a HTML y hosting / landing page (Idea 4)](#fase-4)
- [Fase 5 — Producción del video (Idea 2 + narrativa documental)](#fase-5)
- [Fase 6 — Validación real de Docker (Camino A, ya instalado)](#fase-6)
- [Fase 7 — Consolidación final y checklist maestro de entrega](#fase-7)
- [Apéndice — Convención de commits para esta tanda](#apéndice)

---

<a id="fase-0"></a>
## Fase 0 — Diagnóstico y optimización de latencia de Ollama

### Por qué esto va primero, antes que el chat

Un botón que tarda 30 segundos una vez es tolerable. Un "chat tipo entrevista"
(Idea 3) con 3-4 intercambios a 30s cada uno son dos minutos de silencio en
cámara — mata el ritmo exactamente en la idea que más depende de sentirse "viva".
Hay que entender el problema antes de construir algo que lo va a exponer mucho más.

### Lo que ya sé de tu código (no es especulación, lo leí)

`backend/app/llm_service.py` hoy:
- Llama a `/api/generate` (no streaming: `"stream": false`).
- Usa `"format": "json"` (decodificación con gramática — Ollama valida cada
  token contra el esquema JSON antes de aceptarlo; esto es **objetivamente
  más lento** que generación libre, es un costo real, no un mito).
- **No** setea `keep_alive` → usa el default de Ollama (des-carga el modelo de
  RAM a los 5 minutos de inactividad; la siguiente llamada paga el costo de
  releer el modelo del disco).
- **No** setea `num_predict` → no hay techo al largo de la respuesta.
- Descarta TODA la metadata de tiempos que Ollama devuelve (aunque no
  hagas streaming, la respuesta final trae `total_duration`, `load_duration`,
  `prompt_eval_count`, `prompt_eval_duration`, `eval_count`, `eval_duration`,
  todos en nanosegundos) — hoy es una caja negra, literalmente no hay forma de
  saber en tu código si los 30s son de carga del modelo, de procesar el prompt,
  o de generar la respuesta.

Tu hardware: ThinkPad T480, i5-8365U (4 núcleos / 8 hilos, chip ultrabook de
15W, **sin GPU dedicada** — la Intel UHD 620 no acelera inferencia de LLMs de
forma confiable), 16GB RAM, `my-qwen-3b` (~2.1GB, ya cuantizado).

### Hipótesis, ordenadas por probabilidad — y la más importante

**La hipótesis #1, con diferencia, es que esto no es un bug: es el techo real
de tu hardware.** Un chip ULV de 15W sin GPU, corriendo un modelo de 3B en
CPU, generando ~3-8 tokens/segundo es *normal*, no una anomalía. Una respuesta
JSON de ~100-150 tokens a 4 tok/s son 25-35 segundos — coincide sospechosamente
bien con lo que estás viendo. Te lo digo así de directo porque intentaste
"detectar cosas sin éxito" — es posible que no haya nada que detectar, y que
el tiempo que inviertas en seguir buscando un bug que no existe sea tiempo
que no tenés a 11 días de la entrega. Por eso el paso 1 de abajo es *medir*,
no *arreglar a ciegas*.

Otras hipótesis, en orden de probabilidad después de la #1:

2. **`format: "json"` agrega overhead real** de decodificación restringida.
3. **`load_duration`**: si las llamadas están espaciadas más de 5 minutos
   (típico mientras probás manualmente en el dashboard), cada una paga
   recarga del modelo desde disco.
4. **Plan de energía de Windows / batería**: los chips ULV throttlean fuerte
   en modo "Equilibrado" o sin estar enchufados — factor grande y gratis de
   arreglar.
5. **Contención de recursos — esto es NUEVO desde la semana pasada**: acabás
   de instalar Docker Desktop + WSL2. Aunque no tengas contenedores corriendo,
   Docker Desktop mantiene una VM de WSL2 viva en background consumiendo RAM y
   CPU. Vale la pena medir latencia con Docker Desktop cerrado vs abierto.
6. **Windows Defender / antivirus** escaneando el binario de Ollama o el
   archivo del modelo en cada invocación — menos probable, pero gratis de
   descartar.

### Prompt para OpenCode — instrumentación y medición (hacé esto primero)

```
Contexto: sos OpenCode en D:\AiProject\ai-noc-copilot. El proyecto está
funcionalmente completo. Esta sesión es de DIAGNÓSTICO de latencia del LLM,
no de features nuevas. Leé AGENTS.md y docs/SPEC.md §6 antes de tocar nada.
Todo en español, comandos en PowerShell (Windows es la plataforma real).

OBJETIVO: hoy backend/app/llm_service.py descarta toda la metadata de
tiempos que Ollama devuelve. Sin eso, "tarda 30s" es una caja negra. Arreglá
eso primero, medí, y recién después decidí qué optimizar.

1. Refactor (elimina duplicación real, no es opcional): explain_event() y
   explain_correlated_events() en llm_service.py son casi idénticas
   (mismo payload, mismo manejo de error, mismo parseo de respuesta).
   Extraé un helper privado compartido, por ejemplo:

   async def _call_ollama(prompt: str, *, keep_alive: str = "10m",
                           num_predict: int = 400) -> dict:
       ...

   que:
   - Agregue "keep_alive": keep_alive y "options": {"temperature": 0.1,
     "num_predict": num_predict} al payload (num_predict pone un TECHO
     duro al largo de la respuesta -- no cambia el estilo del prompt,
     solo evita que una respuesta se descontrole en longitud).
   - Después de recibir la respuesta (siempre, no solo en debug), loguee
     con logger.info() en una sola línea estructurada: total_duration,
     load_duration, prompt_eval_count, prompt_eval_duration, eval_count,
     eval_duration (Ollama los devuelve en nanosegundos -- convertilos a
     segundos y a tokens/segundo: eval_count / (eval_duration_ns / 1e9)).
     Ejemplo de línea de log:
     "Ollama timing: total=X.Xs load=X.Xs prompt_eval=X.Xs
      (N tokens) gen=X.Xs (N tokens, X.X tok/s)"
   - explain_event() y explain_correlated_events() pasan a ser wrappers
     finitos sobre este helper (arman su prompt específico, llaman al
     helper, parsean el "response" a JSON igual que antes).

2. NO toques el contrato de las 4 claves del JSON (severity/event_type/
   explanation/recommended_action) -- eso rompería main.py, prohibido por
   SPEC.md §6/§11 sin avisar explícitamente.

3. Corré este script de medición controlada (creá
   scripts/diagnose_llm_latency.py, no hace falta que sea reutilizable,
   es de un solo uso) que haga 4 llamadas a explain_event() con el MISMO
   log de ejemplo y reporte para cada una: total_duration, load_duration,
   eval_count, tokens/segundo:
   - Llamada 1: justo después de "ollama stop my-qwen-3b" (fuerza modelo
     descargado -- esto mide el peor caso, cold start real)
   - Llamada 2: inmediatamente después de la 1 (modelo ya cargado --
     esto mide el mejor caso, modelo caliente)
   - Llamada 3: esperá 6 minutos y repetí (para confirmar si el
     keep_alive de 10m que configuraste en el paso 1 evita la descarga
     que antes pasaba a los 5 min por default)
   - Llamada 4: igual que la 2, pero mientras corrés "ollama ps" en OTRA
     terminal en simultáneo -- pegá el output de "ollama ps" (te dice si
     Ollama está usando CPU 100% o si detectó algo de GPU)

4. Además, reportá (no hace falta scriptearlo, son 2 comandos manuales):
   - powercfg /getactivescheme  (para saber qué plan de energía está activo)
   - Confirmá si el laptop estaba enchufado o en batería durante la prueba

5. Documentá los 4 resultados + el output de ollama ps + el plan de
   energía en un nuevo docs/llm-latency-diagnosis.md -- con la tabla
   completa de números, no solo "quedó mejor". Esto es diagnóstico, no
   optimización a ciegas: quiero los números para decidir el siguiente
   paso con datos reales, no adivinando.

6. pytest tests -v (agregá 2 tests nuevos que SÍ son deterministas y no
   dependen de Ollama real -- mockeá httpx):
   - test_call_ollama_incluye_keep_alive_y_num_predict: verificá que el
     payload enviado a Ollama incluye "keep_alive" y "options.num_predict"
   - test_call_ollama_loguea_metadata_de_tiempos: usando caplog de pytest,
     verificá que se loguea al menos "tok/s" o "tokens/s" en el mensaje
   ruff check limpio.

NO toques el frontend en esta sesión. Al final, proponé el commit y
pegá la tabla completa de resultados en tu respuesta, no solo un resumen.
```

### Qué hacer con los resultados — árbol de decisión

Una vez que tengas la tabla de `docs/llm-latency-diagnosis.md`, estos son los
caminos posibles (decidilo vos con los números reales, esto es una guía):

| Si ves esto... | Significa... | Hacé esto |
|---|---|---|
| Llamada 2 (caliente) tarda ~3-8 tok/s de generación, `load_duration` ≈ 0 | Es el techo normal del hardware — no hay bug | Aceptalo. Aplicá las mitigaciones de abajo para que se *sienta* mejor aunque el número no baje mucho |
| Llamada 1 (fría) tiene un `load_duration` de varios segundos que la 2 no tiene | Confirmado: el modelo se recarga entre llamadas espaciadas | El `keep_alive: "10m"` del paso 1 ya lo resuelve — confirmalo con la llamada 3 |
| Llamada 3 (después de 6 min) sigue teniendo `load_duration` alto | El `keep_alive` no se está aplicando o Ollama lo ignora | Revisar si Ollama respeta el parámetro por versión — probar `keep_alive: -1` (nunca descargar) en vez de "10m" |
| `ollama ps` dice `100% CPU` (esperable) | Confirma que no hay aceleración por GPU — normal en este hardware | No hay nada que "arreglar" ahí, es información, no un problema |
| Plan de energía era "Equilibrado" o estaba en batería | Factor real de throttling | Cambiá a "Máximo rendimiento" y enchufá el laptop antes de la demo — repetí la medición para confirmar la diferencia |
| Tokens/segundo por debajo de ~2 incluso en caliente, enchufado, plan de energía alto | Ahí sí hay algo raro (contención, throttling térmico, Defender) | Repetí con Docker Desktop cerrado, con el Administrador de tareas abierto mirando CPU/RAM durante la llamada, y con Defender en exclusión para la carpeta de Ollama |

### Mitigaciones a aplicar de una, sin importar el diagnóstico

Estas sirven pase lo que pase, porque atacan la *sensación* de lentitud, no
solo el número crudo — esto importa mucho para la demo grabada:

- **`keep_alive` explícito** (ya en el prompt de arriba): evita pagar recarga
  entre acciones de la demo.
- **"Warm-up" antes de grabar**: mandá una llamada de descarte a Ollama (podés
  usar el mismo `curl http://localhost:11434/api/tags` del checklist, o mejor,
  un `POST /api/generate` con un prompt corto) 1-2 minutos antes de prender la
  grabación, para que la primera toma real no pague cold start.
- **`num_predict` como techo**: evita el peor caso de que el modelo se explaye
  de más un día random.
- En la demo grabada: **cortá el clip** durante la espera y mostrá el
  resultado con un salto de edición, en vez de mostrar 30 segundos de spinner
  en tiempo real (ver Fase 5) — esto es más honesto que "editarlo para que
  parezca rápido" y más profesional que aburrir a quien mira el video.

### Pruebas

- `test_call_ollama_incluye_keep_alive_y_num_predict` (mock httpx, assert en el body del request)
- `test_call_ollama_loguea_metadata_de_tiempos` (caplog, assert en el mensaje de log)
- Verificación manual: las 4 mediciones controladas + `ollama ps` + plan de energía, documentadas con números reales en `docs/llm-latency-diagnosis.md`

### Commit propuesto

```
fix: instrumentacion de latencia y keep_alive/num_predict en llm_service

- Extrae helper compartido _call_ollama() (elimina duplicacion entre
  explain_event y explain_correlated_events)
- Agrega keep_alive y num_predict explicitos a cada llamada
- Loguea metadata de tiempos que Ollama ya devolvia y se descartaba
  (load_duration, prompt_eval_duration, eval_duration, tokens/segundo)
- docs/llm-latency-diagnosis.md: medicion controlada de 4 escenarios
  (frio, caliente, post keep_alive, con ollama ps) -- ver conclusiones
- 2 tests nuevos (payload y logging), ruff limpio
```

---

<a id="fase-1"></a>
## Fase 1 — Chat interactivo en el dashboard (Idea 3)

Esta es la fase donde **a propósito** dejo cosas sin decidir — vos las cerrás
con OpenCode en la conversación, iterando. Lo que sí fijo son las decisiones
técnicas que no tiene sentido re-discutir porque ya están resueltas por cómo
está construido el resto del proyecto.

### Lo que SÍ está decidido (no lo cuestiones con el agente, aplícalo)

1. **Usar `/api/chat` de Ollama, no `/api/generate`.** `/api/chat` maneja
   nativamente un array de `messages` con roles (`system`/`user`/`assistant`)
   — es la forma correcta de hacer multi-turno, en vez de concatenar a mano
   el historial dentro de un string de prompt como hace `/api/generate`.

2. **Streaming, no respuesta de una sola vez.** Con 20-30s por respuesta
   (Fase 0), una respuesta no-streaming en un chat se siente "colgado". Con
   `"stream": true`, Ollama devuelve fragmentos JSON línea por línea
   (`{"message": {"content": "..."}, "done": false}` ... hasta un
   `"done": true` final que trae la metadata de tiempos de la Fase 0 —
   logueala ahí también). FastAPI expone esto con `StreamingResponse`;
   Streamlit lo consume naturalmente con `st.chat_message(...).write_stream(generator)`
   — le pasás un generador que yieldea strings y Streamlit los va pintando
   solo. Esto cambia la PERCEPCIÓN de velocidad enormemente aunque el tiempo
   total sea el mismo — ver texto aparecer palabra por palabra se siente vivo,
   ver un spinner fijo 25 segundos se siente roto.

3. **El chat está anclado a datos reales (grounding), nunca es un chat
   libre.** Esto no es una preferencia de diseño, es el mismo principio que
   ya está en `threat_explainer.txt` ("No inventes IPs, reglas ni contexto
   que no esté presente en el log") y en SPEC.md ("el LLM solo explica y
   recomienda, nunca decide solo"). El system prompt del chat tiene que
   inyectar el/los evento(s) reales sobre los que se está preguntando (raw
   log, severity/event_type/pattern ya calculados) como contexto fijo, y
   prohibir explícitamente inventar información de red que no esté ahí. Si
   la Idea 3 (formato "entrevista") le pregunta al copiloto "¿por qué
   marcaste esto como alta severidad?", la respuesta tiene que basarse en el
   dato real que generó esa clasificación, no en una alucinación nueva.

4. **No hace falta tabla nueva en la base de datos.** El historial de la
   conversación vive en `st.session_state` del lado del frontend (memoria
   de la sesión de Streamlit) — el backend es stateless: cada request de
   chat manda el historial completo (igual patrón que ya usa este mismo tipo
   de documento cuando hablás conmigo: mandar todo el estado relevante en
   cada llamada, no asumir memoria del lado del servidor). Esto es
   consistente con la decisión ya tomada de "sin tabla nueva" para
   `correlation_group` — mismo criterio de simplicidad.

5. **`keep_alive` alto durante una sesión de chat.** Las lecciones de la
   Fase 0 aplican con más fuerza acá: una "entrevista" de 4-5 turnos con
   recarga de modelo entre cada uno sería insoportable.

### Lo que queda ABIERTO — para que decidas vos con OpenCode

El prompt de abajo le dice explícitamente a OpenCode que **pare antes de
tocar el frontend** y te haga preguntas concretas. Estas son las decisiones
que probablemente te va a plantear (pensalas antes para ir más rápido en la
iteración, pero no hace falta que las resuelvas ahora mismo):

- **Alcance del chat**: ¿preguntás sobre UN evento puntual (`/events/{id}/chat`),
  sobre un grupo de correlación completo, o es un chat "general" sobre el
  estado actual del dashboard (eventos recientes, estadísticas)? Para la
  Idea 3 (formato entrevista sobre un incidente) lo más natural es
  **por evento o por grupo de correlación** — pero es tu llamada.
- **Dónde vive en la UI**: ¿pestaña propia, panel lateral, un modal que se
  abre desde cada evento, o integrado en la pestaña "Acerca del proyecto"
  de la Fase 2?
- **Persona/tono del system prompt**: ¿el copiloto responde como un colega
  técnico, como un analista formal, tiene algún nombre/personalidad para la
  demo? Esto afecta directamente cómo se siente la Idea 3 en cámara.
- **Preguntas sugeridas o campo libre**: ¿mostrás 2-3 botones con preguntas
  típicas ("¿por qué es alta severidad?", "¿qué debería hacer ahora?") para
  que la demo no dependa de que se te ocurra algo bueno en vivo, o es 100%
  campo de texto libre?
- **Renderizado**: ¿las respuestas del copiloto se muestran como texto plano
  o Markdown (listas, negritas)?

### Prompt para OpenCode

```
Contexto: sos OpenCode en D:\AiProject\ai-noc-copilot. Leé AGENTS.md,
docs/SPEC.md y el resultado de la sesión de diagnóstico de latencia
(docs/llm-latency-diagnosis.md) antes de arrancar -- las decisiones de
keep_alive de esa sesión aplican acá también. Todo en español.

Vas a construir un chat interactivo con el LLM local dentro del dashboard
(nueva feature, no estaba en el ROADMAP original -- agregala como
"Fase 5.10 -- Chat interactivo" cuando la cierres).

═══════════════════════════════════════════════════
PARTE A -- Backend (esto SÍ está decidido, implementalo tal cual)
═══════════════════════════════════════════════════

1. Nuevo endpoint POST /events/{event_id}/chat en main.py que:
   - Recibe {"message": str, "history": list[{"role": str, "content": str}]}
     (el frontend manda el historial completo cada vez -- no hay estado en
     el backend, mismo criterio que ya se uso para no crear tablas nuevas).
   - Busca el evento real en la DB (404 si no existe, mismo patrón que
     /events/{id}/analyze).
   - Arma un system message con el contexto real del evento: raw_message,
     severity/event_type/ai_explanation si ya fue analizado, y si tiene
     correlation_group, incluí también el patron clasificado
     (classify_port_pattern) y cuantos eventos tiene el grupo. Reglas del
     system prompt (no negociable, mismo principio que threat_explainer.txt):
     nunca inventar IPs, puertos, o contexto de red que no esté en los datos
     reales entregados.
   - Llama a Ollama /api/chat (NO /api/generate) con stream=true, keep_alive
     alto (usa la misma constante que definiste en la Fase 0 de
     llm_service.py, no hardcodees un valor nuevo suelto).
   - Devuelve un StreamingResponse de FastAPI que va yieldeando cada
     fragmento de contenido a medida que Ollama lo manda (no acumules todo
     y lo mandes de una al final -- el streaming tiene que llegar
     streameado hasta el cliente).
   - Al final del stream (cuando Ollama manda "done": true), logueá la
     metadata de tiempos igual que en la Fase 0 (reusa el helper si aplica).
   - Manejo de errores: si Ollama no responde, mismo patrón de
     LLMAnalysisError -> 502 que ya usa el resto de la API.

2. Agregá esta funcion a llm_service.py (o un módulo nuevo chat_service.py
   si preferís separarlo, tu criterio de organización de código, pero
   reusá _call_ollama o el patrón de manejo de errores/timeouts existente,
   no dupliques la configuración de httpx de _ollama_client_kwargs()).

3. Tests (mockeando httpx, no dependen de Ollama real corriendo):
   - test_chat_evento_inexistente_devuelve_404
   - test_chat_incluye_contexto_del_evento_en_system_prompt (verificá que
     el raw_message del evento real aparece en el payload mandado a Ollama)
   - test_chat_usa_api_chat_no_generate (verificá la URL del endpoint
     llamado a Ollama)
   - test_chat_propaga_error_502_si_ollama_falla

pytest tests -v verde, ruff check limpio, antes de seguir a la Parte B.

═══════════════════════════════════════════════════
PARTE B -- Frontend (PARAR ACÁ, esto es flexible a propósito)
═══════════════════════════════════════════════════

NO implementes la UI del chat todavía. En tu respuesta de esta sesión,
hacele estas preguntas concretas a Marcos y esperá su respuesta antes de
tocar frontend/dashboard.py:

1. ¿El chat es por evento individual, por grupo de correlación, o ambos
   (un botón "Preguntarle al copiloto" en cada expander de evento Y en
   cada grupo del histórico de correlación)?
2. ¿Dónde va en la UI -- pestaña nueva, dentro de cada expander de evento,
   modal, o integrado a la pestaña "Acerca del proyecto"?
3. ¿Querés preguntas sugeridas (botones con preguntas típicas) además del
   campo de texto libre, para asegurar que la demo tenga algo bueno para
   mostrar aunque no se te ocurra qué preguntar en el momento de grabar?
4. ¿Algún tono/persona específico para el system prompt, o "analista
   técnico directo" (el tono que ya usan el resto de las explicaciones)
   está bien?

Cuando tengas las respuestas, implementá con st.chat_message() +
st.write_stream() (Streamlit soporta pasarle un generador/iterador de
strings y lo va pintando incrementalmente -- así es como conseguís el
efecto "está escribiendo en vivo" en vez de esperar la respuesta completa).
httpx con stream=True del lado del cliente Streamlit para consumir el
StreamingResponse del backend sin bloquear.

Verificación final de la Parte B: pytest sigue en verde, ruff limpio,
py_compile dashboard.py, y probá el chat EN VIVO al menos 3 veces seguidas
sobre el mismo evento para confirmar que el keep_alive evita que la 2da y
3ra respuesta paguen recarga de modelo (mirá los logs de timing).
```

### Pruebas

- Backend: los 4 tests listados arriba (mockeados, deterministas)
- Manual: 3+ turnos seguidos sobre el mismo evento, confirmando en los logs
  que solo el primer turno paga `load_duration` alto (si el `keep_alive`
  está bien aplicado)
- Manual: hacer una pregunta cuyo dato NO está en el log (ej. "¿qué otros
  ataques hizo esta IP el mes pasado?") y confirmar que el copiloto dice
  que no tiene esa información en vez de inventarla — este es el test más
  importante del principio de "grounding", probalo a propósito

### Commit propuesto (partido en dos, backend primero)

```
feat: endpoint de chat streaming por evento (POST /events/{id}/chat)

Usa /api/chat de Ollama (multi-turno nativo) con streaming real via
StreamingResponse. Contexto grounded en el evento real (raw_message,
severity, patron de correlacion si aplica) -- nunca inventa datos de red
no presentes. Stateless: el frontend manda el historial completo en cada
turno. keep_alive alto para evitar recarga de modelo entre turnos de una
misma conversacion. 4 tests nuevos, ruff limpio.
```
```
feat: UI de chat interactivo en el dashboard

[completar despues de la iteracion con Marcos sobre alcance/UX -- ver
Parte B del prompt]
```

---

<a id="fase-2"></a>
## Fase 2 — Pestaña "Acerca del proyecto" (Idea 1)

Esto lo pediste explícitamente para la Idea 1 (sala de guerra, todo pasa
dentro del dashboard, sin PowerPoint tradicional). Es una pestaña nueva en
Streamlit que reemplaza lo que normalmente serían "las slides de contexto".

### Contenido sugerido

- Un diagrama de arquitectura (embebido como imagen — usá el que generemos
  en la Fase 3, exportado a PNG/SVG).
- 3-4 decisiones de diseño clave, presentadas como "por qué", no como lista
  técnica seca: por qué Ollama nativo y no Docker, por qué el LLM nunca
  decide solo (heurísticas deterministas primero), por qué air-gapped es un
  requisito y no una preferencia.
- Línea de tiempo del ROADMAP (de qué fase a qué fase), quizás como una
  barra de progreso visual en vez de una tabla.
- Stack técnico como badges/chips (FastAPI, SQLModel, Streamlit, Ollama,
  Qwen 3B) — visualmente rápido de leer.
- Un link/QR (si lo generás) al repo de GitHub.

### Prompt para OpenCode

```
Contexto: sos OpenCode en D:\AiProject\ai-noc-copilot. Leé
docs/branding.md e isotype.md (paleta --ainoc-*) antes de arrancar.

Agregá una pestaña nueva "ℹ️ Acerca del proyecto" en frontend/dashboard.py
(usando st.tabs si el dashboard no las usa todavía, o la estructura de
navegación que ya exista -- revisá el archivo primero, no asumas).
Contenido (usá copy real del proyecto, no placeholder):

1. Sección "El problema": 2-3 frases sobre logs de pfSense sin analizar
   en un entorno air-gapped (sacá el texto de SPEC.md §1, no lo reescribas
   de cero).
2. Sección "Arquitectura": un placeholder de imagen (st.image) para
   docs/diagrams/arquitectura.png -- el archivo todavía no existe, lo va a
   generar Marcos en otra sesión (Fase 3 del plan), dejá el código
   preparado para cuando exista, con manejo de error si el archivo no está
   (no rompas el dashboard si falta la imagen).
3. Sección "Decisiones de diseño clave": 3-4 tarjetas o expanders con
   título corto + explicación de 1-2 frases cada una. Sacá el contenido de
   AGENTS.md (la sección de "gotchas no obvios" y las decisiones
   documentadas) y de SPEC.md §3 y §11 -- son las decisiones reales del
   proyecto, no inventes nuevas.
4. Sección "Stack técnico": FastAPI, SQLModel, SQLite, Streamlit, Ollama +
   Qwen 3B, Plotly -- como st.badge o chips con color de la paleta
   --ainoc-* existente.
5. Sección "Roadmap": una versión visual simplificada (barra de progreso
   con st.progress o similar) del estado de fases en ROADMAP.md -- no
   repliques la tabla completa, es un resumen de alto nivel.
6. Link al repo de GitHub (0xmarcosdev/ai-noc-copilot) como st.link_button.

Consistencia visual: reusá los helpers de estilo que ya existen en
dashboard.py (badges de severidad, paleta), no inventes un estilo nuevo
para esta pestaña sola.

pytest tests -v (no debería afectar tests de backend), ruff check,
py_compile dashboard.py. Proponé el commit al final.
```

### Pruebas

- `py_compile dashboard.py` sin errores
- Verificación manual: la pestaña carga sin romper el resto del dashboard
  incluso si `docs/diagrams/arquitectura.png` todavía no existe (fallback
  gracioso, no un traceback en pantalla — esto importa mucho si vas a
  grabar en vivo)

### Commit propuesto

```
feat: pestaña "Acerca del proyecto" en el dashboard

Nueva seccion informativa (problema, arquitectura, decisiones de diseño,
stack, roadmap resumido) para presentar el proyecto sin salir del
dashboard -- pensada para la demo grabada en formato inmersivo (sin
slides tradicionales). Placeholder de imagen para el diagrama de
arquitectura, con fallback si el archivo aun no existe.
```

---

<a id="fase-3"></a>
## Fase 3 — Diagramas estilo pizarra sin saber dibujar (Idea 5)

Esta fase **no es para OpenCode** — es creativa/visual, la hacés vos (o yo te
ayudo directamente generando el código). Te explico el camino más corto para
llegar al look "pizarra a mano alzada" sin tener que dibujar nada a pulso.

### El pipeline que te recomiendo (verificado, funciona hoy)

**Texto → Mermaid → Excalidraw → PNG/SVG.**

1. Vos me describís el diagrama (o yo te lo propongo a partir de lo que ya
   sé del proyecto) y yo te genero la sintaxis de **Mermaid** — es texto
   plano tipo:
   ```
   flowchart LR
     A[pfSense / generador sintético] -->|syslog UDP| B[Backend FastAPI]
     B --> C[(SQLite)]
     B -->|evento sin analizar| D[Ollama local]
     D -->|explicacion JSON| B
     B --> E[Dashboard Streamlit]
   ```
2. Vas a **excalidraw.com**, abrís el menú (☰) → buscás la opción
   **"Mermaid to Excalidraw"** (está integrada nativamente en la app, no
   hace falta instalar nada) → pegás el texto Mermaid.
3. Excalidraw genera el diagrama como formas **nativas y editables**
   (rectángulos, flechas, texto) en su estilo hand-drawn — no es una imagen
   pegada, podés mover cada caja, cambiarle el color, agregar anotaciones a
   mano encima. Esto solo funciona perfecto con diagramas tipo *flowchart*
   (que es exactamente lo que necesitás para arquitectura/flujos) — otros
   tipos de diagrama Mermaid se insertan como imagen en vez de formas
   editables, para tu caso de uso no importa.
4. Exportás desde Excalidraw como PNG o SVG con fondo transparente
   (Export → "background transparent") y lo guardás en `docs/diagrams/`.

**Pedime a mí los diagramas y te los genero ahora mismo en cualquier
momento** — no hace falta que sepas Mermaid, solo describime qué querés
mostrar y te devuelvo el texto listo para pegar.

### Los 3 diagramas que te recomiendo para este proyecto específico

1. **Arquitectura general**: generador/pfSense → syslog UDP → FastAPI →
   SQLite / Ollama → Streamlit. (El que armé de ejemplo arriba, te lo puedo
   afinar).
2. **El corazón de la demo — evento aislado vs. correlacionado**: un evento
   solo entrando y saliendo como "severity: low", vs. 10 eventos agrupados
   entrando y saliendo como "severity: high" con el ícono de patrón. Este
   es el diagrama que más vale la pena tener bien pulido — es literalmente
   el punto de venta del proyecto (SPEC.md §7).
3. **Filosofía determinista + LLM**: un flujo mostrando "heurística
   determinista decide QUÉ pasó" → "LLM solo explica CÓMO comunicarlo" —
   para dejar clara la decisión de diseño más importante del proyecto
   (nunca al revés).

### Herramientas alternativas (si Excalidraw no te convence)

- **Eraser.io (DiagramGPT)**: le escribís en lenguaje natural "diagrama de
  arquitectura con FastAPI, SQLite, Ollama y Streamlit" y genera el
  diagrama directo, sin pasar por Mermaid. Tiene capa gratuita.
- **napkin.ai**: similar, texto → visual automático, buena opción si querés
  algo más ilustrativo/menos técnico para la sección de "el problema".

### Pruebas / verificación

- Los 3 PNG/SVG existen en `docs/diagrams/` con nombres consistentes
  (`arquitectura.png`, `evento-vs-correlacion.png`, `deteccion-determinista-vs-llm.png`)
- Se ven bien tanto en fondo claro como oscuro (exportá con fondo
  transparente para que funcionen en Slidev/dashboard sin importar el tema)
- El de la pestaña "Acerca del proyecto" (Fase 2) los está usando de verdad,
  no quedó el placeholder

### Commit propuesto

```
docs: diagramas de arquitectura y flujo (Excalidraw)

Agrega docs/diagrams/ con 3 diagramas exportados: arquitectura general,
evento aislado vs correlacionado, y filosofia deteccion determinista +
explicacion LLM. Generados via pipeline Mermaid -> Excalidraw.
```

---

<a id="fase-4"></a>
## Fase 4 — Slidev, export a HTML, hosting y/o landing page (Idea 4)

### Slidev — instalación y estructura

Requiere Node.js ≥ 20.12 (ya lo tenés por WSL2/npm de trabajos anteriores,
confirmá con `node --version`).

```powershell
npm init slidev@latest
```

Te va a pedir un nombre de carpeta (ej. `ai-noc-slides`) y arranca un
proyecto con `slides.md` como archivo principal. Para desarrollar en vivo:

```powershell
npm run dev
```

Abre en `http://localhost:3030` con hot-reload — vas editando el markdown y
se actualiza solo.

**Estructura de deck sugerida** (cada `---` es una slide nueva en Slidev):

1. Título + tu nombre + curso
2. El problema (logs sin analizar, air-gapped, sin LLM en la nube posible)
3. Arquitectura (embebé el diagrama SVG de la Fase 3 con `![](./diagrams/arquitectura.svg)`)
4. La limitación que resolviste (evento aislado = low, correlacionado = high)
   — embebé el segundo diagrama acá, es tu slide más importante
5. Decisión de diseño: heurística determinista + LLM que explica, nunca decide
6. **Slide de transición a demo en vivo** — un texto grande tipo "→ demo en
   vivo" y ahí cambiás de ventana al dashboard real (Slidev soporta
   presentador con notas — `npm run dev -- --remote` si querés controlar
   desde el celular mientras mostrás la pantalla principal)
7. Resultados / tests / cobertura
8. Roadmap y qué quedó para después (multi-sucursal, RAG sobre runbooks —
   sacalo de la sección "Fuera de alcance" de SPEC.md §2, mostrar que sabés
   dónde termina el MVP a propósito suma puntos)
9. Cierre + repo + gracias

Slidev corre sobre Vue, así que podés embeber componentes interactivos de
verdad si querés (no solo imágenes estáticas) — para un proyecto de curso
probablemente no haga falta, pero está la opción si te copa.

### Exportar a HTML estático

```powershell
npm run build
```

Esto genera una carpeta `dist/` con una SPA (Single Page Application) 100%
estática — HTML/CSS/JS, sin necesitar Node corriendo para verla. Se puede
abrir localmente:

```powershell
npx vite preview
```

O simplemente hostearla en cualquier servicio de archivos estáticos.

### Hosting gratis — Render (el que mencionaron en el curso)

Confirmé que Render sigue teniendo **static sites gratis en 2026**, sin
tarjeta de crédito, con CDN y SSL incluido, y a diferencia de los "web
services" gratis de Render (que se "duermen" a los 15 min de inactividad),
**los static sites NO tienen ese problema** — quedan siempre disponibles,
ideal para esto.

Pasos:
1. Subí la carpeta `dist/` (o todo el proyecto de Slidev) a un repo de
   GitHub — puede ser el mismo repo del proyecto en una carpeta
   `docs/slides/`, o uno aparte, tu preferencia.
2. En Render: New → Static Site → conectá el repo.
3. Build command: `npm install && npm run build`
4. Publish directory: `dist`
5. Deploy — te da una URL tipo `ai-noc-copilot-slides.onrender.com`.

**Alternativas igual de gratis y sin fricción** si Render te da problemas:
GitHub Pages (ya tenés el repo ahí, cero configuración extra) o Netlify
(arrastrar y soltar la carpeta `dist/` en netlify.com/drop, literalmente
sin cuenta).

### La idea nueva que se te ocurrió: landing page en vez de (o además de) las slides

Es una idea genuinamente buena — un landing page bien armado se defiende
distinto que una presentación, se siente más "producto terminado" que
"trabajo de curso". Dos caminos:

**Camino A — me lo pedís a mí.** Te genero un landing page completo en un
solo archivo HTML (con la paleta `--ainoc-*` que ya tenés en `branding.md`,
usando las guías de diseño que ya sigo para este tipo de piezas) como
artifact — lo iterás conmigo en esta misma conversación o en una nueva,
ajustando secciones hasta que te guste, y después lo hosteás igual que el
deck de Slidev (Render/Netlify/GitHub Pages, mismo proceso). Es el camino
más directo porque no depende de que aprendas una herramienta nueva.

**Camino B — herramientas de generación asistida por IA** si querés algo
que vos mismo edites de forma más visual/no-code: **v0.dev** (de Vercel) o
**lovable.dev** generan landing pages a partir de una descripción en texto,
con capas gratuitas — pero son herramientas nuevas y sus límites gratuitos
cambian seguido, confirmá el estado actual antes de invertir tiempo ahí.

Mi recomendación honesta: si el objetivo es tenerlo listo y confiable para
el 4 de sept, el Camino A (pedírmelo a mí) es el de menor riesgo — cero
curva de aprendizaje nueva, iteramos rápido, y ya conozco el branding del
proyecto.

### ¿Slides (Slidev) o landing page — o los dos?

Dado que dijiste que vas a probar todas las ideas y después elegís/combinás:
- El **deck de Slidev** funciona mejor como acompañamiento en vivo durante
  la presentación (navegás con flechas mientras hablás).
- El **landing page** funciona mejor como pieza que dejás circulando
  después — un link que el profesor o compañeros puedan visitar solos, sin
  vos narrando. Sirve como "portada" del proyecto en el README también.

No compiten, son para momentos distintos. Si el tiempo aprieta cerca del
4 de sept, priorizá el que vayas a *usar en vivo* — probablemente el deck.

### Pruebas

- `npm run build` termina sin errores, `dist/` se ve bien con
  `npx vite preview`
- El sitio deployado en Render/Netlify carga correctamente desde una red
  distinta a la tuya (probalo desde el celular con datos móviles, no wifi,
  para descartar problemas de caché local)
- Si hacés el landing page conmigo: probalo en una ventana angosta
  (responsive) antes de darlo por terminado

### Commit propuesto

```
docs: deck de Slidev y/o landing page para la presentacion

Agrega docs/slides/ (proyecto Slidev con el deck de 9 slides) y/o
docs/landing/ (landing page standalone). Build estatico verificado,
deployado en [Render/Netlify/GitHub Pages] en [URL].
```

---

<a id="fase-5"></a>
## Fase 5 — Producción del video (Idea 2 + narrativa documental)

`docs/demo-script.md` ya existe (8 escenas, 8-10 min) — esta fase es sobre
**cómo grabarlo y editarlo** para que se sienta producido, no como una
captura de pantalla cruda.

### Narración con ElevenLabs — cómo no quedarte sin cuota

Confirmé el plan gratis actual: **10,000 caracteres por mes**, ~10 minutos
de audio, acceso a las 100+ voces estándar de la librería (sin clonación de
voz, eso es de pago). Un guion de 4-6 minutos narrado a ritmo normal ronda
los 4,000-6,500 caracteres — **te entra en un mes con margen**, pero:

- **No regeneres de más.** Los caracteres no rollean al mes siguiente y no
  hay forma de comprar más en el plan gratis — si regenerás la misma frase
  5 veces probando entonaciones, se te va la cuota rápido.
- Escribí el guion de narración COMPLETO y revisado (ortografía, ritmo,
  dónde van las pausas) *antes* de generar audio — tratalo como el guion
  final, no un borrador que vas a regenerar iterando.
- Contá caracteres antes de generar (cualquier procesador de texto te da el
  conteo) para no sorprenderte a mitad de mes.
- Uso comercial en el plan gratis requiere atribución a ElevenLabs — para
  un trabajo de curso esto no debería ser un problema, pero tenelo presente
  si vas a publicar el video más ampliamente después.

### Música y efectos — opciones si buscás algo distinto a stock

Ya dijiste que vas a buscar vos, así que solo te dejo opciones por si te
sirven: **Pixabay Music** y **Mixkit** (gratis, sin atribución obligatoria,
buena curación) para música/SFX de stock. Si preferís algo generado y
único en vez de stock: **Suno** o **Udio** generan música original a partir
de una descripción de texto, ambos con capa gratis limitada — para 30-60
segundos de intro/cierre alcanza de sobra.

### Herramientas de edición de video — comparación rápida

| Herramienta | Gratis | Mejor para | Nota |
|---|---|---|---|
| **DaVinci Resolve** | Sí, sin marca de agua | Edición seria, corrección de color, tiene IA integrada (Magic Mask, Voice Isolation, Scene Cut Detection) | Curva de aprendizaje más alta, pero es la opción "de verdad profesional" gratis |
| **CapCut Desktop** | Sí (versión desktop) | Edición rápida, subtítulos automáticos con buena precisión, B-roll sugerido por IA | Más simple que Resolve, ideal si el tiempo aprieta |
| **Descript** | Capa gratis limitada (revisá minutos actuales antes de comprometerte) | Editar video editando el TEXTO de la transcripción (borrás una palabra del texto y borra ese segmento de video) + limpieza de audio con IA (Studio Sound) | Es el más raro/potente de la lista — vale la pena si tu narración tiene muchos "eh" que limpiar |
| **Clipchamp** | Sí, viene incluido en Windows 11 | Cortes básicos + subtítulos automáticos, cero instalación | La opción de "no quiero instalar nada nuevo" |

Mi sugerencia concreta para vos: **CapCut Desktop** para el corte principal
(rápido, subtítulos automáticos gratis — que además suman accesibilidad y
se ven prolijos en un video de curso) + si tu narración de ElevenLabs
necesita limpieza o si grabás algo de audio propio con ruido de fondo,
**Descript** solo para esa limpieza puntual (Studio Sound), después volvés
a CapCut para el ensamblado final.

### Trucos de grabación (retomando lo que ya hablamos, ahora aplicado al guion real)

- **OBS Studio** con escenas separadas (terminal / navegador / pantalla
  completa) — cambiás con hotkeys, evita zoom digital en edición.
- **ZoomIt** para zoom real + anotaciones en vivo sobre el JSON de
  respuesta o el ícono de patrón (🎯 vs 📡) — este es el momento de la
  demo donde más vale la pena un zoom marcado, es tu punto de venta.
- Grabá **por escena** (las 8 del guion, como clips separados), no de
  corrido — si te trabás en la escena 4, repetís solo esa.
- Sobre los 20-30s de espera del LLM (Fase 0): grabá la espera real UNA
  vez para tener el material honesto, pero en edición **cortala a 3-4
  segundos con un salto de corte** (no aceleres el video con timelapse,
  se ve artificial — un corte seco es más limpio) — mostrás que existe el
  tiempo de espera sin aburrir a quien mira.
- Windows Terminal con oh-my-posh, tema de alto contraste, fuente 16-18pt.

### Checklist de producción (además del checklist pre-grabación que ya tenés en demo-script.md)

- [ ] Guion de narración final escrito y contado en caracteres (< 10,000)
- [ ] Audio de ElevenLabs generado en una sola pasada por escena (evitar regenerar)
- [ ] Clips de pantalla grabados por escena (las 8 de demo-script.md)
- [ ] Música/SFX elegidos y con licencia de uso confirmada
- [ ] Cortes de las esperas del LLM aplicados (no timelapse, corte seco)
- [ ] Subtítulos generados (CapCut/Clipchamp automático) y revisados a mano
- [ ] Exportado en 1080p mínimo, formato mp4

### Pruebas

- Reproducir el video final de punta a punta sin editar más nada, cronometrado
- Mostrárselo a alguien que no conozca el proyecto y preguntarle si entendió
  el punto central (evento aislado vs. correlacionado) — es la prueba real
  de que la narrativa funciona

### Commit propuesto

```
docs: guion de narracion final y checklist de produccion de video

Agrega docs/narracion-final.md (guion contado en caracteres para
ElevenLabs) y actualiza docs/demo-script.md con el checklist de
produccion (musica, subtitulos, cortes de espera del LLM).
```

---

<a id="fase-6"></a>
## Fase 6 — Validación real de Docker (Camino A, ya instalado)

Ya instalaste Docker Desktop + WSL2 (Camino A). Esto es lo que falta para
cerrar de verdad el ítem de `ROADMAP.md` que hoy dice "inspeccionado
estáticamente, no ejecutado en runtime".

### Pasos

1. Abrí Docker Desktop una vez, confirmá que usa el backend WSL2 (Settings
   → General).
2. Ollama tiene que escuchar en todas las interfaces, no solo localhost:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'User')
   ```
   Cerrá Ollama por completo (bandeja del sistema → Quit) y reabrilo.
   Confirmá que sigue respondiendo local: `curl http://localhost:11434/api/tags`
3. Desde la raíz del repo:
   ```powershell
   docker compose up --build
   ```
4. Mirá los logs: el backend tiene que pasar el healthcheck (`/health`)
   antes de que el frontend arranque.
5. Abrí `http://localhost:8501`, generá logs sintéticos desde tu
   PowerShell normal (`generate_fake_logs.py` corre en el host, no en
   Docker, y manda UDP al puerto 5514 que el compose expone), y confirmá
   que "Explicar con IA" funciona desde el contenedor hacia tu Ollama nativo.
6. Si agregaste el chat de la Fase 1, probalo también desde Docker — el
   streaming tiene que atravesar el proxy de Docker sin cortarse (esto es
   un buen test de estrés real para esa feature).

### Qué hacer con el resultado

- Actualizá `docs/docker-validation.md`: cambiá la limitación #1 de "no se
  puede probar en este equipo" a "probado en runtime el [fecha]" — con una
  nota de cualquier ajuste que hayas tenido que hacer.
- Marcá el ítem correspondiente en `ROADMAP.md` como `[x]`.
- Sacá una captura del `docker compose up` corriendo limpio — es evidencia
  para la entrega.

### Pruebas

- `docker compose up --build` levanta sin errores
- Healthcheck del backend pasa
- Flujo completo (ingesta → análisis → correlación → chat si existe)
  funciona igual que en Opción A (venv)

### Commit propuesto

```
docs: docker compose validado en runtime

Actualiza docs/docker-validation.md: probado end-to-end con Docker
Desktop + WSL2 (Camino A). Ollama bindeado a 0.0.0.0:11434 para ser
alcanzable desde el contenedor via host.docker.internal. ROADMAP.md
actualizado.
```

---

<a id="fase-7"></a>
## Fase 7 — Consolidación final y checklist maestro de entrega

Cuando termines lo de arriba, esto es lo que queda para cerrar del todo:

- [ ] `ROADMAP.md` refleja el estado real de TODAS las fases de este documento
- [ ] `docs/plan-produccion-entrega.md` (este archivo, si lo subiste al repo)
      actualizado con qué se hizo vs. qué quedó de las 5 ideas originales
- [ ] Video final exportado y en un lugar accesible (subilo aunque sea sin
      publicar, como respaldo — no dependas de una sola copia local)
- [ ] Deck de Slidev y/o landing page deployados y el link probado desde
      otra red
- [ ] Docker probado en runtime, no solo por inspección
- [ ] Ensayo de la presentación en voz alta, cronometrado — con el material
      real (dashboard con la pestaña nueva, chat funcionando, diagramas)
- [ ] Evidencia de uso de IA exportada (esta conversación incluida)

### Orden de prioridad si el tiempo aprieta

Si llegás apretado al 4 de sept, este es el orden de qué NO podés sacrificar
vs. qué es "nice to have":

**No negociable:** Fase 0 (latencia, aunque sea solo el diagnóstico sin
mitigar todo), Fase 6 (Docker probado de verdad), el video con el guion que
ya tenés (aunque sea sin narración de ElevenLabs — un video mudo con
subtítulos también funciona).

**Muy recomendable pero no fatal si falta:** Fase 1 (chat interactivo) —
es la idea más ambiciosa técnicamente, si el tiempo no da, un video sólido
con las escenas 1-8 ya planeadas sigue siendo una entrega fuerte.

**Bonus / lo que te diferencia del resto de la clase:** Fase 2 (pestaña
"Acerca del proyecto"), Fase 3 (diagramas pulidos), Fase 4 (deck +
landing page) — suman mucho a la percepción de producto terminado, pero
ninguna rompe el proyecto si no llegás.

---

<a id="apéndice"></a>
## Apéndice — Convención de commits para esta tanda

Mismo criterio que ya usa el proyecto (`ROADMAP.md`): un commit por idea
completa, prefijo `feat:`/`fix:`/`docs:`/`test:`, no acumules cambios de
fases distintas en un mismo commit aunque los hagas en la misma sesión de
OpenCode — son conceptualmente separables y el historial de git debería
reflejar eso, no solo el resultado final.

Etiquetá una versión nueva (`git tag`) solo si alguna de estas fases
representa un salto de funcionalidad que querés marcar (ej. el chat
interactivo podría justificar un `v0.6.0`) — las fases puramente de
presentación/producción (3, 4, 5, 6) probablemente no necesitan tag propio,
son parte del entregable, no del versionado del software.