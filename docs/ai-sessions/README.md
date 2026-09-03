# Sesiones de IA — evidencia de uso

Para ver los momentos más representativos de uso de IA en decisiones críticas, ir directo a la sección **[## Los 5 momentos clave — IA en la toma de decisiones](../DEVLOG.md#los-5-momentos-clave-ia-en-la-toma-de-decisiones)** en DEVLOG.md.

Cada archivo de esta carpeta es una sesión clave con una herramienta de IA, exportada como texto (copiar/pegar el intercambio relevante, no hace falta la conversación completa si es muy larga — basta el fragmento que muestra la contribución real). Nombre de archivo: `AAAA-MM-DD-herramienta-tema.md`.

## Índice

| Fecha | Herramienta | Tema | Fase | Evidencia de decisión | ⭐ |
|---|---|---|---|---|---|
| 2026-08-10 | Claude | Diseño arquitectura, evaluación 7 propuestas | Fase 0 | Definición MVP, descarte sobrealcance | |
| 2026-08-11 | Perplexity | Formato filterlog pfSense | Fase 3 | Verificación BNF oficial + código fuente | |
| 2026-08-12 | Qwen | Debug rutas Windows, bug carpeta data | Fase 1 | Diagnóstico bug real SQLite mkdir | |
| 2026-08-16 | DeepSeek | Preguntas para chat dashboard | Fase 4 | 3 preguntas + pseudocódigo, 1 en /summary | |
| 2026-08-16 | (varias) | Detección picos z-score | Fase 5.5 | Diseño evaluado y descartado por scope creep | |
| 2026-08-17 | Claude | Correlación, beaconing, heurísticas DNS | Fase 5.5 | Features completas detección patrones | |
| 2026-08-19 | OpenCode | Docker, ingesta manual, .dockerignore | Fase 5.6 | Validación Docker Opción B, POST /ingest, UI | |
| 2026-08-20 | OpenCode | Búsqueda, filtros, paginación | Fase 5.7 | GET /events paginado, filtros, session_state | |
| 2026-08-20 | OpenCode | Ingesta manual (sesión adicional) | Fase 5.6 | Tests ingesta, integración /correlate | |
| 2026-08-20 | OpenCode | Diseño visual: branding e isotipo | Fase 5 (UI) | Paleta colores, CSS, isotipo animado SVG | |
| 2026-08-22 | OpenCode | Resumen visual dashboard | Fase 5 (UI) | Documentación diseño visual | |
| 2026-08-23 | OpenCode | Fases 5.8 y 5.9: correlación + gráficos | Fases 5.8, 5.9 | Histórico correlación, plotly, CSV/JSON, reporte | |
| 2026-08-24 | OpenCode | Verificación final y guion demo | Fase 6 (prep.) | Confirmación stdlib, regresión 31/31, guion demo | |
| 2026-08-25 | Grok | Revamp visual dashboard, debug lookup chat | Fase 5.10 | Tabs, tema claro/oscuro, mitación GET /events/{id} | |
| 2026-08-26 | Qwen 3.7 | Chat fix alucinación + nested expanders | Fase 5.10 | Inyección contexto, system prompt, popovers | ⭐ |
| 2026-08-26 | Qwen 3.7 | UI Tabs, persistencia correlación, UX chat | Fase 5.10 | Selectbox dinámico grupos, st.rerun() post-correlate | |
| 2026-08-27 | Gemini Flash | Métricas rendimiento LLM, tab Rendimiento | Fase 5.10 | GET /performance/stats, trade-offs hardware | |
| 2026-08-28 | Gemini Notebook | Robustez escenarios, exclusión mutua API | Fase 5.5/5.8 | Filtro action=block, random.sample portscan | ⭐ |
| 2026-08-29 | Grok + DeepSeek | UI correlación tabular, estado Streamlit | Fase 5.11 | st.radio nav, tabla dataframe, caché explicaciones | |
| 2026-08-31 | OpenCode | Limpieza y consolidación pre-MVP | Fase 6 | Limpieza dumps, alineación docs, plotly solo frontend | |

### Otros documentos de diseño

| Archivo | Contenido |
|---|---|
| `branding.md` | Paleta de colores (--ainoc-*), CSS, especificación visual |
| `isotype.md` | Isotipo animado SVG, especificación de animación |
| `Resumen de builds — Fases A y B del dashboard-opencode.md` | Resumen ejecutivo mejoras visuales dashboard |
| `Resumen de la Fase A — Implementación completada-opencode.md` | Detalle implementación Fase A |
| `2026-08-19-propuestas-evaluadas.txt` | Propuestas arquitectura evaluadas y descartadas |
| `Sesión completada — Pre-entrega Fase 6.md` | Inspección Docker, README, SPEC, evidencia IA (Momento #3) |

## Sesiones documentadas solo en DEVLOG.md (sin export separado)

| Fecha | Descripción |
|---|---|
| 10 ago 2026 | Día 1 — Alcance MVP, esqueleto repo, decisión Ollama nativo |
| 11-12 ago 2026 | Día 2 — Sin pfSense lab, generador sintético, Perplexity filterlog |
| 15-16 ago 2026 | Día 3 — Python 3.14 fix, httpx keep-alive fix, SPEC.md creado |
| 16 ago 2026 | Día 4 — POST /correlate, ROADMAP.md, generador IP fija por lote |
| 19 ago 2026 | Día 5 — Versiones fijadas, scripts PowerShell arranque |
| 17-18 ago 2026 | Día 6 — Beaconing/DNS, z-score descartado, AGENTS.md fusión OpenCode (Momento #4) |
| 19-20 ago 2026 | Día 7 — Docker inspección, ingesta manual, Ollama modelo registrado |
| 20 ago 2026 | Día 8 — GET /events paginado, dashboard session_state, 20 tests |
| 23 ago 2026 | Día 9 — classify_port_pattern, correlation_group, SPEC §7 fix (Momento #1) |
| 23 ago 2026 | Día 10 — UI histórico correlación, expanders + íconos |
| 23 ago 2026 | Día 11 — /summary extendido, plotly, exportar, reporte on-demand |
| 24 ago 2026 | Día 12 — Verificación stdlib, demo-script.md, ROADMAP Fase 6 |

## Cómo agregar una sesión nueva

1. Copia el intercambio relevante (prompt + respuesta) a un archivo nuevo aquí.
2. Agrega una fila al índice de arriba.
3. Si la sesión se usó para el proyecto, referencia también el commit donde se incorporó (ej. "ver commit `abc1234`").

No hace falta capturar cada mensaje de cada conversación — el objetivo es mostrar evidencia real de uso de IA en decisiones concretas, no un archivo por cada intercambio trivial.