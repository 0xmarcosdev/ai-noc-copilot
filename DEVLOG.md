# DEVLOG

## Cómo se delegó el trabajo entre herramientas de IA

Basado en AGENTS.md — roles operativos:

- **Claude**: arquitectura, coherencia general, revisión de código, generación de prompts para OpenCode, defensa de decisiones en SPEC.md
- **OpenCode (Mimo v2.5-free)**: ejecución agéntica de código, implementación de features, debugging, validación Docker, limpieza
- **Perplexity**: investigación verificada contra fuentes primarias (BNF oficial, código fuente pfSense)
- **DeepSeek**: tareas de alto volumen / repetitivas (generación de preguntas, tests)
- **Gemini API**: generación de datos sintéticos
- **Kimi**: procesamiento de documentos largos
- **Grok / ChatGPT**: respaldo y segunda opinión

**Regla operativa**: cuando una herramienta propone un cambio que contradice una decisión ya documentada en SPEC.md, Claude lo señala explícitamente antes de proceder (no se reemplaza en silencio). La delegación sigue el principio: determinismo en la detección, LLM solo para explicación; todo air-gapped; Windows como plataforma real.

---

## Día 1 — 10 ago 2026

**Asistente(s) de IA**: Claude  
**Fase**: Fase 0 (Diseño y alcance)

**Contexto**: Inicio del proyecto, evaluación de 7 propuestas de arquitectura sobredimensionadas (Elastic, Suricata/Zeek completo, multi-sucursal real, modelos 7B+).

**Qué se hizo**:
- Definido MVP: FastAPI + SQLModel/SQLite + Streamlit + Ollama nativo
- Generado esqueleto del repo: listener syslog UDP, modelo NetworkEvent, servicio LLM, dashboard, docker-compose
- Decisión de arquitectura: Ollama corre nativo en host (ya instalado con modelo), no en contenedor
- Tests iniciales pytest pasando (4/4)

**Decisión de diseño / aprendizaje clave**: Ollama nativo ahorra espacio en disco (SSD limitado) y evita complejidad de networking sin beneficio. Documentado en SPEC.md §3.

**Verificación**: 4/4 tests ✅

---

## Día 2 — 11-12 ago 2026

**Asistente(s) de IA**: Perplexity, Qwen  
**Fase**: Fase 1 (Ingesta y pipeline base) / Fase 3 (Datos sintéticos)

**Contexto**: No hay pfSense de laboratorio (los reales están en producción). Necesidad de datos de prueba realistas.

**Qué se hizo**:
- Perplexity: verificado formato filterlog de pfSense contra BNF oficial (docs.netgate.com) y código fuente GitHub (parse_firewall_log_line en syslog.inc)
- Construido scripts/generate_fake_logs.py con 3 escenarios (normal, bruteforce, portscan) fieles al formato verificado
- Pipeline validado end-to-end: ingesta UDP → SQLite → /analyze → Ollama (my-qwen-3b:latest) → explicación
- Bug corregido: SQLite no creaba carpeta `data/` → fix en main.py con Path.mkdir()
- Agregado python-dotenv + .env.example para variables de entorno en Windows

**Decisión de diseño / aprendizaje clave**: Usar generador sintético con formato verificado, no pfSense real. Vía segura para logs reales: exportar manual + sanitizar + POST /events/ingest (SPEC §8).

**Verificación**: Pipeline end-to-end validado contra Ollama real

---

## Día 3 — 15-16 ago 2026

**Asistente(s) de IA**: Qwen, Claude  
**Fase**: Fase 2 (LLM local)

**Contexto**: Pipeline básico funcionando, pero evento individual de fuerza bruta se clasifica como severity "low" (limitación esperada sin correlación).

**Qué se hizo**:
- Detectado problema de entorno: Python 3.14 rompe SQLModel/Pydantic (PEP 649) → fijado venv a Python 3.11/3.12
- Diagnosticado y resuelto: httpx keep-alive causaba "Server disconnected" → deshabilitado max_keepalive_connections=0, timeouts separados en llm_service.py
- Confirmado: evento SSH aislado → severity "low"; grupo correlacionado → severity "high"
- Creado docs/SPEC.md como referencia única (spec-driven development)

**Decisión de diseño / aprendizaje clave**: Fijar Python 3.11/3.12 (consistente con Dockerfile python:3.11-slim) en vez de parchear código para 3.14. Detección determinista + LLM para explicación, no al revés.

**Verificación**: Pipeline validado end-to-end contra Ollama real; low vs high confirmado como evidencia clave

---

## Día 4 — 16 ago 2026

**Asistente(s) de IA**: Claude  
**Fase**: Fase 4 (Correlación de eventos)

**Contexto**: Evento aislado de fuerza bruta = low. Necesidad de agrupar por IP atacante + ventana temporal.

**Qué se hizo**:
- Construido endpoint POST /events/correlate: agrupa por IP atacante real (extract_attacker_ip desde raw_message), envía lote al LLM
- Creado ROADMAP.md (checklist fases + versionado vMAJOR.MINOR.PATCH)
- Detectado bug en generador sintético: usaba IP atacante distinta por evento → corregido para fijar IP por lote
- Prueba repetida: 10 eventos agrupados, severity: high, patrón identificado
- Agregados tests para /correlate, limpieza de duplicados en tests
- Actualizados ROADMAP.md y SPEC.md (Fase 4 completa)

**Decisión de diseño / aprendizaje clave**: Correlación usa IP real extraída del raw_message (regex), NO source_ip del paquete UDP (que es el pfSense). Ver SPEC §4 y §7.

**Verificación**: /correlate funcionando, tests pasando

---

## Día 5 — 19 ago 2026

**Asistente(s) de IA**: OpenCode  
**Fase**: Fase 1/5 (Infraestructura scripts + UI)

**Contexto**: Dependencias conflictivas entre FastAPI/Starlette/Streamlit; necesidad de scripts de arranque en Windows.

**Qué se hizo**:
- Fijadas versiones compatibles: fastapi==0.115.0, starlette==0.38.6, streamlit==1.39.0
- Creados scripts start-backend.ps1, start-frontend.ps1, start-all.ps1
- Creado frontend/.env con BACKEND_URL=http://localhost:8000
- Automatizada carga de .env en scripts PowerShell

**Verificación**: Scripts arrancan backend/frontend correctamente en Windows

---

## Día 6 — 17-18 ago 2026

**Asistente(s) de IA**: Claude, OpenCode  
**Fase**: Fase 5.5 (Detección extendida)

**Contexto**: Correlación básica funcionando. Extender detección a beaconing y DNS sospechoso.

**Qué se hizo**:
- Implementados POST /events/detect-beaconing (coeficiente de variación de intervalos) y POST /events/detect-suspicious-dns (entropía de Shannon, dns_heuristics.py)
- Formato DNS de pfSense verificado con Perplexity (Unbound + dnsmasq)
- Principio declarado: detección siempre determinista; LLM solo redacta explicación
- Evaluado y descartado conscientemente: detección de picos con z-score (scope creep — reimplementaba ML de anomalías excluido del MVP)
- 4 escenarios sintéticos nuevos: beacon, dns_dga, dns_normal, vpn_flapping
- Bug corregido: generador DGA no era suficientemente aleatorio para disparar heurística
- Creado AGENTS.md (Claude) y fusionado con versión OpenCode (/init) → OpenCode encontró bugs reales: contaminación DB entre tests y 2 archivos basura comiteados
- ROADMAP: Fase 5.5 cerrada

**Decisión de diseño / aprendizaje clave**: Detección determinista (regex/entropía/estadística) — el LLM nunca decide, solo explica. z-score descartado por scope creep.

**Verificación**: 4 escenarios nuevos, detección beaconing/DNS validada

---

## Día 7 — 19-20 ago 2026

**Asistente(s) de IA**: OpenCode  
**Fase**: Fase 5.6 (Ingesta manual) + Docker

**Contexto**: Validación despliegue Docker (Opción B) y feature de ingesta manual para logs reales (SPEC §8).

**Qué se hizo**:
- Validación Docker por inspección estática (Docker Desktop no instalado): corregidos .dockerignore (excluye .venv ~421MB), healthcheck backend, streamlit actualizado, prerequisitos Ollama/puertos en README
- Feature ingesta manual: POST /events/ingest (pegar/subir líneas como eventos sin analizar) + UI en dashboard + 5 tests
- Planificada con OpenCode modo Plan: received_at=utcnow, ingesta pasiva (no auto-correlaciona)
- Validación en vivo: Ollama sin modelo registrado (OLLAMA_MODELS mal configurado) → diagnóstico paso a paso, modelo registrado con `ollama create`
- Correlación real confirmada: severity "high" para 6 eventos fuerza bruta ingeridos (51s); análisis individual: severity "low" (18.7s)
- ROADMAP: Fase 5.6 casi completa

**Decisión de diseño / aprendizaje clave**: Ingesta manual materializa vía segura SPEC §8 — sanitizar IPs antes de pegar, received_at=utcnow para que ventanas de correlación funcionen de inmediato.

**Verificación**: Correlación real low vs high confirmada (51s vs 18.7s)

---

## Día 8 — 20 ago 2026

**Asistente(s) de IA**: Grok, OpenCode  
**Fase**: Fase 5.7 (Búsqueda, filtros y paginación)

**Contexto**: Lista de eventos creciendo, necesidad de paginación y filtros en backend y frontend.

**Qué se hizo**:
- GET /events extendido: limit/offset/q/severity/event_type/only_unanalyzed/id_from/id_to/received_at_from/received_at_to/sort_by/sort_dir → `{total, limit, offset, items}`
- Backend: parche llegó con feature de ingesta borrada accidentalmente → restaurada desde commit anterior y reaplicado limpio
- Dashboard: parsea `{items, total}`, filtros + paginación con session_state (resetea página al cambiar filtros)
- Tests: test_list_events actualizado + nuevo test_list_events_pagination_and_filters (q, severity, only_unanalyzed, event_type, limit/offset)
- Suite completa 20 tests en verde, ruff limpio
- ROADMAP: Fase 5.7 creada, casi completa

**Verificación**: 20/20 tests ✅, ruff ✅

---

## Día 9 — 23 ago 2026

**Asistente(s) de IA**: Claude  
**Fase**: Fase 5.8 (Persistencia y clasificación de correlación)

**Contexto**: Retomada tras sesión OpenCode que dejó Fase 5.8 a medio construir: correlation_group en NetworkEvent, GET /events/correlation-history stub, 5 tests escritos pero classify_port_pattern no existía (NameError) y /correlate no escribía correlation_group.

**Qué se hizo**:
- Implementado classify_port_pattern: heurística determinista por ratio puertos destino distintos (≤0.3 fuerza_bruta, ≥0.7 escaneo_puertos, <3 eventos o zona intermedia → indeterminado)
- POST /events/correlate ahora asigna correlation_group (contador global creciente, sin reutilizar IDs) y pasa patrón como contexto explícito al LLM
- Corregida inconsistencia en SPEC.md §7: umbrales y migración ALTER TABLE no codificada → documentada como limitación conocida
- 29/29 tests en verde, ruff limpio, DB de desarrollo recreada
- ROADMAP: Fase 5.8 backend completa, falta UI dashboard para histórico

**Decisión de diseño / aprendizaje clave**: classify_port_pattern 100% determinista (sin LLM), umbrales como constantes en main.py. SQLModel.metadata.create_all() no migra columnas en SQLite existente — borrar .db en desarrollo.

**Verificación**: 29/29 tests ✅, ruff ✅, py_compile ✅

---

## Día 10 — 23 ago 2026

**Asistente(s) de IA**: OpenCode  
**Fase**: Fase 5.8 (UI histórico correlación)

**Contexto**: Backend de Fase 5.8 completo. Falta sección dashboard que consuma /events/correlation-history.

**Qué se hizo**:
- Implementada sección "Histórico de correlación" en frontend/dashboard.py: consume GET /events/correlation-history al cargar
- Cada grupo en expander con ícono (🎯 fuerza_bruta, 📡 escaneo_puertos, ❓ indeterminado), IPs, severidad, ventana temporal, IDs
- Botón "Correlacionar eventos sin analizar" se mantiene intacto
- 29/29 tests en verde, ruff limpio, py_compile sin errores
- ROADMAP: Fase 5.8 cerrada, Fase 5.9 (Estadísticas y gráficos) como siguiente

**Verificación**: 29/29 tests ✅, ruff ✅, py_compile ✅

---

## Día 11 — 23 ago 2026

**Asistente(s) de IA**: OpenCode  
**Fase**: Fase 5.9 (Estadísticas y gráficos)

**Contexto**: Cerrar Fase 5.8 y abordar Fase 5.9 (recomendaciones #10 y #12: panel enriquecido, gráficos, exportar, reporte on-demand).

**Qué se hizo**:
- Backend: GET /summary extendido con by_event_type, time_series, correlated_count, individual_count (sin romper contrato) + 2 tests nuevos (31/31 total)
- Gráficos: evaluado plotly vs altair → plotly por customización y soporte nativo Streamlit, 100% offline (sin CDN), documentado en SPEC §9
- Frontend: 3 gráficos interactivos (pie severidad, barras tipos, línea temporal), exportar CSV/JSON, reporte on-demand determinista en Markdown (sin LLM)
- ruff limpio backend+frontend, 31/31 tests en verde
- ROADMAP: Fase 5.9 cerrada

**Decisión de diseño / aprendizaje clave**: Reporte on-demand NO pasa por LLM — es 100% determinista (conteos, distribuciones). LLM redacta explicaciones de eventos/grupos, no informes estadísticos. Plotly 100% offline.

**Verificación**: 31/31 tests ✅, ruff ✅, py_compile ✅

---

## Día 12 — 24 ago 2026

**Asistente(s) de IA**: OpenCode  
**Fase**: Fase 6 (Preparación entrega)

**Contexto**: Proyecto funcionalmente completo (Fases 0-5.9). Verificación pre-grabación y documentación final.

**Qué se hizo**:
- Confirmado dashboard.py usa solo stdlib (csv, json, io) para exportar — NO pandas
- Creado docs/demo-script.md: guion 8 escenas, 8-10 min, checklist pre-grabación 7 ítems
- ROADMAP actualizado: ítems Fase 5.8 completados, pendientes Fase 6 annotados (evidencia IA, Docker, grabación, ensayo)
- Regresión final: 31/31 tests ✅, ruff ✅, py_compile ✅
- Sesión exportada a docs/ai-sessions/2026-08-24-opencode-verificacion-y-guion-demo.md

**Verificación**: 31/31 tests ✅, ruff ✅, py_compile ✅, stdlib confirmado

---

## Sesión 14 — 25 ago 2026

**Asistente(s) de IA**: Grok  
**Fase**: 5.10 (Revamp visual dashboard + debug lookup chat)

**Contexto**: Dashboard con scroll vertical infinito. Chat fallaba por falta de GET /events/{id} en backend.

**Qué se hizo**:
- Diagnosticado backend: no existe GET /events/{event_id} → chat hacía 404; mitigación frontend con cascada (GET /events?id_from=N&id_to=N&limit=5 + búsqueda en últimos 200)
- Revamp UI: tabs (Eventos/Chat/Correlación), tema claro/oscuro CSS, filtros como radios, chat en bloque HTML scrolleable, tipografía JetBrains Mono + IBM Plex Sans, gráficos Plotly con hover/tema
- Verificación sugerida: curl health, GET /events?id_from=X&id_to=X, GET /events/X (esperado 404 hoy)
- Próximos pasos: añadir GET /events/{event_id} y chat por grupo dedicado

**Decisión de diseño / aprendizaje clave**: st.tabs no conserva pestaña al rerun → más adelante se cambió a st.radio + session_state. Chat sobre grupo necesita endpoint dedicado o resolver a event_id del grupo.

**Verificación**: 37/37 tests ✅ (tras añadir GET /events/{id} en sesión posterior)

---

## Sesión 15 — 26 ago 2026

**Asistente(s) de IA**: Qwen 3.7  
**Fase**: 5.10 (Chat interactivo + corrección alucinación LLM)

**Contexto**: Error Streamlit "Expanders may not be nested" en histórico correlación + alucinación crítica del LLM en chat (confundía grupo #5 con #1, IP incorrecta, latencia 53.1s).

**Qué se hizo**:
- Fix 1: st.expander anidados → st.popover en 2 ubicaciones (Correlación e Histórico)
- Fix 2: Reset historial al cambiar destino (session_state.chat_prev_dest)
- Fix 3: Cache session_state (chat_groups_cache, chat_events_cache) evita llamadas extra al backend
- Fix 4: System prompt robusto con 6 reglas obligatorias (solo info contexto, nunca inventar, respetar clasificación, ignorar mensajes previos de otro grupo, español técnico, admitir si falta info) + formato respuesta estructurado
- Fix 5: Inyección de contexto en cada mensaje del usuario (--- CONTEXTO DEL GRUPO #X: IP, patrón, severidad, eventos, puertos)
- Fix 6: Chips de preguntas dinámicos contextuales ("¿Qué significa el grupo #5?" vs genérico)

**Decisión de diseño / aprendizaje clave**: Alucinación del LLM resuelta con inyección explícita de contexto por mensaje + system prompt con reglas estrictas. Popovers evitan error de expanders anidados.

**Verificación**: Alucinaciones 100% → 0%, consistencia 100%, latencia 53.1s → 43.2s (-19%), UI sin errores. Export: docs/ai-sessions/2026-08-26-qwen37-chat-fix-alucinacion.md

---

## Sesión 16 — 26 ago 2026

**Asistente(s) de IA**: Qwen 3.7  
**Fase**: 5.10 (UI Tabs + persistencia correlación + UX chat)

**Contexto**: Continuación de sesión 15. Migración a layout por tabs, corrección bugs de persistencia y UX chat.

**Qué se hizo**:
- Migración a st.tabs: Eventos | Chat | Correlación (separación contextos, reduce carga cognitiva)
- Refinamiento visual CSS: variables :root, tipografía dual, badges semánticos, frame chat con scroll interno
- Bug histórico vacío: DB vieja sin columna correlation_group (limitación SQLite create_all) → documentado reset DB + st.rerun() post-correlación
- Bug chat por grupo: number_input obligaba a adivinar ID → selectbox dinámico desde /correlation-history con metadatos legibles
- Flujo correlación end-to-end verificado: Generación → Correlación → Historial persistente → Chat contextual sin alucinaciones

**Verificación**: Dashboard pulido, fluido completo verificado. Export: docs/ai-sessions/2026-08-26-qwen37-ui-tabs-chat.md

---

## Sesión 17 — 27 ago 2026

**Asistente(s) de IA**: Gemini Flash  
**Fase**: 5.10 (Métricas rendimiento LLM + pestaña Rendimiento)

**Contexto**: Latencia LLM ~18-38s. Necesidad de visibilidad de hardware/trade-offs para presentación.

**Qué se hizo**:
- Análisis hardware: NVIDIA MX150 2GB VRAM vs modelo 3.4B Q4_K_M (~2.4GB) → 74% capas en CPU, 26% GPU, ~5.2 tok/s
- Backend: GET /performance/stats expone LLMTiming (total/load/prompt_eval/gen seconds, tokens/s, modelo, modo) + matriz trade-offs (actual vs Qwen 1.5B vs Q3_K_M vs CPU Q8)
- Frontend: Tab ⚡ Rendimiento con KPIs, diagnóstico hardware, tarjetas trade-offs con badge recomendación, gráfico Plotly temporal + tabla historial
- Validación: 37/37 tests ✅

**Decisión de diseño / aprendizaje clave**: Cuello de botella es físico (VRAM), no código (cliente reutilizado, keep_alive, mediciones por fases). Detección determinista no depende de velocidad LLM.

**Verificación**: 37/37 tests ✅. Export: docs/ai-sessions/2026-08-27-gemini-flash-performance.md

---

## Sesión 18 — 28 ago 2026

**Asistente(s) de IA**: Gemini Notebook  
**Fase**: 5.5/5.8 (Robustez escenarios sintéticos + exclusión mutua API)

**Contexto**: Conflictos entre escenarios beacon/portscan y correlación; inestabilidad en generador portscan.

**Qué se hizo**:
- Backend: correlate_events() filtra estrictamente action="block" (ignora pass/out de beaconing) — resuelve conflicto que marcaba beaconing como fuerza_bruta
- Beaconing: restaurado agrupamiento por tupla (src, dst, dport) para análisis intervalos intacto
- Generador sintético: pool puertos ampliado a 40 (COMMON_PORTS), muestreo sin reposición (random.sample) en portscan → ratio variación consistentemente 1.0
- Tests: test_correlate_ignores_pass_action_events aislado e independiente
- SPEC.md §7 actualizado: correlación determinista solo opera sobre paquetes bloqueados

**Decisión de diseño / aprendizaje clave**: Exclusión mutua en API — /correlate solo ve action=block; /detect-beaconing solo ve action=pass/out. Generador portscan determinista con random.sample.

**Verificación**: 100% tests en verde (pytest tests -v). Escenarios beacon/portscan predecibles y excluyentes. Export: docs/ai-sessions/2026-08-28-gemini-notebook-beacon-portscan.md

---

## Sesión 19 — 29-30 ago 2026

**Asistente(s) de IA**: Grok + DeepSeek  
**Fase**: 5.11 (UI correlación tabular + estado Streamlit + pestañas extra)

**Contexto**: Histórico correlación en expanders. Inestabilidad estado UI tras st.rerun() (explicar, correlacionar, tema).

**Qué se hizo**:
- Navegación: st.tabs → st.radio + session_state.main_tab (conserva pestaña activa al rerun). Pestañas: Eventos | Chat | Correlación | Rendimiento | Acerca
- Correlación: tabla paginada st.dataframe (on_select, selección fila), columnas #/Severidad/Patrón/IPs/Puertos/Eventos/Desde/Hasta/Explicación (✓/⏳), panel detalles fijo bajo tabla
- Estado: caché sesión corr_expl/corr_expl_by_ids (correlation-history no trae explanation), corr_selected_gid mantiene foco, banner dismissible post-correlate
- Notificaciones: _push_notification + notification_log (máx 50, sin emojis en string), header con botones ↻/tema compactos
- CSS: variables tema, foco fila cian marca (#0891B2), fixes NameError por llaves en f-string, UI fantasma, propiedades mal formadas
- Bugs corregidos: salto a Eventos tras rerun, emoji duplicado, NameError background, CSS mal formado

**Verificación**: Correlacionar → grupos en tabla → seleccionar → explicar → un panel, pestaña conservada. Export: docs/ai-sessions/2026-08-29-grok-deepseek-ui-correlacion.md

---

## Sesión 20 — 31 ago 2026

**Asistente(s) de IA**: OpenCode  
**Fase**: 6 (Limpieza y consolidación pre-MVP)

**Contexto**: Repo con archivos temporales, exports duplicados, documentación desalineada.

**Qué se hizo**:
- Eliminados 4 dumps crudos OpenCode de raíz (268KB, 169KB, 1KB, 48KB)
- Eliminadas 5 transcripciones >50KB de docs/ai-sessions/ (261KB, 340KB, 352KB, 207KB, 106KB)
- Eliminados duplicados branding.md/isotype.md en ai-sessions (canónicos en docs/)
- Actualizado docs/ai-sessions/README.md reflejando solo archivos que quedan
- ROADMAP: Fase 5.6 cerrada (lote real opcional), Fase 5.11 cerrada, versiones actualizadas
- SPEC.md: dashboard actualizado (pestañas, comportamiento Correlación tabla+caché+limitaciones), fecha 31 ago 2026
- AGENTS.md: extract_attacker_ip verificado (main.py:51), plotly solo en frontend/requirements.txt
- plotly eliminado de backend/requirements.txt
- Comentarios en main.py, llm_service.py, chat_service.py, dashboard.py revisados (español, precisión, coherencia SPEC/AGENTS)

**Verificación**: Pendiente ruff check + pytest tests -v desde backend/

---

## Sesión 21 — 3 sept 2026

**Asistente(s) de IA**: OpenCode (Mimo v2.5-free)  
**Fase**: 6 (Evidencia IA y documentación final)

**Contexto**: Proyecto funcionalmente completo. DEVLOG.md y docs/ai-sessions/ necesitaban estandarización para servir como evidencia de uso de IA en la presentación final.

**Qué se hizo**:
- Agregado preámbulo "Cómo se delegó el trabajo entre herramientas de IA" basado en AGENTS.md (roles: Claude arquitectura/coherencia, OpenCode ejecución agéntica, Perplexity investigación verificada, DeepSeek alto volumen, Gemini API datos sintéticos, Kimi docs largos, Grok/ChatGPT respaldo)
- Reformateadas 19 entradas DEVLOG a template fijo (mismos encabezados, orden, español)
- Renumeradas sesiones 14-20 en orden cronológico real (25→31 ago): Grok revamp(25), Qwen fix alucinación(26), Qwen UI tabs(26), Gemini Flash performance(27), Gemini Notebook exclusión mutua(28), Grok+DeepSeek UI correlación(29-30), OpenCode limpieza(31)
- Comprimidas sesiones 14-20 a 8-10 líneas c/u; detalle técnico movido a 7 exports nuevos en docs/ai-sessions/
- Agregada sección final "Los 5 momentos clave — IA en la toma de decisiones" con 5 casos verificables (classify_port_pattern, alucinación chat grupo #5, plotly docker, contaminación DB tests, conflicto beaconing/correlación)
- Creados 7 exports nuevos en docs/ai-sessions/ para sesiones 14-20
- Reescrito docs/ai-sessions/README.md: índice 19 filas, columna "Evidencia de decisión", ⭐ en momentos #2 y #5, enlace a 5 momentos, lista sesiones solo en DEVLOG
- Agregada caption en landing/index.html bajo FRANJA DE LOGOS con link absoluto a DEVLOG.md en GitHub

**Decisión de diseño / aprendizaje clave**: La evidencia de uso de IA debe ser verificable (commits, tests, archivos concretos), no narrativa. Estandarizar el DEVLOG permite al jurado ver la trazabilidad real de decisiones críticas sin leer conversaciones completas.

**Verificación**: 40/40 tests ✅, ruff ✅, py_compile ✅, anclas internas validadas

---

## Los 5 momentos clave — IA en la toma de decisiones

### 1. Clasificación bruteforce vs portscan — decisión de diseño determinista
- **Cuándo**: Día 9 (23 ago) — [ver entrada](#día-9-23-ago-2026)
- **Herramienta**: Claude (implementación) + OpenCode (tests previos)
- **El problema**: Un evento correlacionado necesitaba distinguir fuerza bruta (mismo puerto repetido) de escaneo (puertos distintos) sin usar LLM para la clasificación.
- **Cómo se resolvió**: Heurística `classify_port_pattern` en main.py basada en ratio puertos destino distintos (≤0.3 fuerza_bruta, ≥0.7 escaneo_puertos, indeterminado en zona media o <3 eventos). Umbrales como constantes configurables.
- **Por qué importa**: Cumple el principio central del proyecto: **detección determinista, LLM solo explica** (SPEC §6). El LLM recibe el patrón ya clasificado como contexto, nunca decide solo.

### 2. Alucinación del chat confundiendo grupo #5 con grupo #1
- **Cuándo**: Sesión 15 (26 ago) — [ver entrada](#sesión-15-26-ago-2026)
- **Herramienta**: Qwen 3.7 (detectó y resolvió)
- **El problema**: Al consultar sobre Grupo #5 (fuerza_bruta, high), el LLM respondía "indeterminado", IP 198.51.100.74 (del Grupo #1), referenciaba grupo incorrecto. Latencia 53.1s.
- **Cómo se resolvió**: Inyección de contexto explícito en cada mensaje del usuario (--- CONTEXTO DEL GRUPO #X: IP, patrón, severidad, eventos, puertos), system prompt con 6 reglas obligatorias, reset de historial al cambiar destino, cache session_state, popovers en lugar de expanders anidados.
- **Por qué importa**: Demuestra que **el LLM no tiene memoria fiable entre turnos** — el contexto debe inyectarse explícitamente en cada request. Fix técnico que mantiene la arquitectura determinista (el LLM sigue sin decidir, solo explica con contexto correcto).

### 3. plotly ausente en frontend/requirements.txt rompiendo docker compose up
- **Cuándo**: Archivo `docs/ai-sessions/Sesión completada — Pre-entrega Fase 6.md` (Parte 0)
- **Herramienta**: OpenCode (validación Docker estática)
- **El problema**: Frontend usaba plotly para gráficos interactivos pero la dependencia solo estaba en backend/requirements.txt. Al hacer `docker compose up`, el contenedor frontend fallaba al importar plotly.
- **Cómo se resolvió**: Creado frontend/requirements.txt con streamlit, httpx, plotly pineados; actualizado frontend/Dockerfile para usar requirements.txt; README Opción A actualizado.
- **Por qué importa**: Valida el principio **air-gapped** — plotly es 100% offline (se instala via pip, sirve assets desde paquete local, sin CDN). La validación estática de Docker (sin Docker Desktop) detectó el fallo antes de runtime.

### 4. Contaminación de DB entre corridas de test
- **Cuándo**: Día 6 (17-18 ago) — [ver entrada](#día-6-17-18-ago-2026)
- **Herramienta**: OpenCode (fusionando AGENTS.md con /init)
- **El problema**: Tests usaban DB temporal en `%TEMP%\ai_noc_test.db` pero el archivo no se borraba entre corridas → conteos de grupos inesperados en /correlate, /detect-beaconing, /detect-suspicious-dns.
- **Cómo se resolvió**: Agregado borrado automático del archivo al inicio de la sesión de tests en test_api.py (líneas 13-20): `if os.path.exists(_TEST_DB_PATH): os.remove(_TEST_DB_PATH)`.
- **Por qué importa**: **Aislamiento de tests** es requisito para evidencia confiable. Bug real encontrado por IA cruzada (OpenCode revisando código de Claude) — demuestra valor de revisión multi-herramienta.

### 5. Conflicto de correlación agrupando eventos de beaconing (pass) como fuerza bruta
- **Cuándo**: Sesión 18 (28 ago) — [ver entrada](#sesión-18-28-ago-2026)
- **Herramienta**: Gemini Notebook
- **El problema**: /events/correlate agrupaba eventos de beaconing (action=pass, direction=out) y los marcaba como fuerza_bruta por baja variación de puertos hacia el C2. Esto los marcaba analyzed=True, impidiendo que /events/detect-beaconing los procesara.
- **Cómo se resolvió**: Filtrado estricto en correlate_events(): solo procesa eventos con action="block" (extraído via extract_connection_summary). Beaconing restaurado a agrupamiento por tupla (src, dst, dport) para análisis de intervalos.
- **Por qué importa**: **Exclusión mutua en la API** — cada detector opera sobre su dominio semántico (block vs pass/out). Evita falsos positivos y pisadas de estado (analyzed=True) entre detectores. Documentado en SPEC §7.