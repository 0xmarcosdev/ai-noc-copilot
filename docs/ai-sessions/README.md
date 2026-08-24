# Sesiones de IA — evidencia de uso

Cada archivo de esta carpeta es una sesión clave con una herramienta de IA,
exportada como texto (copiar/pegar el intercambio relevante, no hace falta
la conversación completa si es muy larga -- basta el fragmento que muestra
la contribución real). Nombre de archivo: `AAAA-MM-DD-herramienta-tema.md`.

## Índice

| Fecha | Herramienta | Tema | Fase | Contribución |
|---|---|---|---|---|
| 2026-08-10 | Claude | Diseño de arquitectura, evaluación de 7 propuestas | Fase 0 | Definición del MVP, descarte de sobrealcance |
| 2026-08-11 | Perplexity | Formato filterlog de pfSense | Fase 3 | Verificación con fuente oficial (BNF + código fuente) |
| 2026-08-12 | Qwen | Debug de rutas en Windows, bug de carpeta `data/` | Fase 1 | Diagnóstico correcto de un bug real |
| 2026-08-16 | DeepSeek | Preguntas para el chat del dashboard | Fase 4 | 3 preguntas + pseudocódigo, 1 incorporada al `/summary` |
| 2026-08-16 | (herramienta sin especificar) | Detección de picos con z-score | Fase 5.5 | Diseño evaluado y conscientemente descartado por scope creep |
| 2026-08-17 | Claude | Correlación de eventos, beaconing, heurísticas DNS | Fase 5.5 | Features completas de detección de patrones |
| 2026-08-19 | OpenCode | Docker, ingesta manual, .dockerignore | Fase 5.6 | Validación Docker (Opción B), POST /events/ingest, UI dashboard |
| 2026-08-20 | OpenCode | Búsqueda, filtros, paginación | Fase 5.7 | GET /events paginado, filtros q/severity/event_type, session_state |
| 2026-08-20 | OpenCode | Ingesta manual (sesión adicional) | Fase 5.6 | Tests de ingesta, integración con /correlate |
| 2026-08-20 | OpenCode | Diseño visual: branding e isotipo | Fase 5 (UI) | Paleta de colores, CSS, isotipo animado SVG |
| 2026-08-22 | OpenCode | Resumen visual del dashboard | Fase 5 (UI) | Documentación de diseño visual |
| 2026-08-23 | OpenCode | Fases 5.8 y 5.9: correlación + gráficos | Fases 5.8, 5.9 | Histórico correlación, plotly, CSV/JSON, reporte on-demand |
| 2026-08-24 | OpenCode | Verificación final y guion de demo | Fase 6 (prep.) | Confirmación stdlib (sin pandas), regresión 31/31, guion demo |

### Otros documentos de diseño

| Archivo | Contenido |
|---|---|
| `branding.md` | Paleta de colores (--ainoc-*), CSS, especificación visual |
| `isotype.md` | isotipo animado SVG, especificación de animación |
| `Resumen de builds — Fases A y B del dashboard-opencode.md` | Resumen ejecutivo de las mejoras visuales del dashboard |
| `Resumen de la Fase A — Implementación completada-opencode.md` | Detalle de la implementación de la Fase A |
| `2026-08-19-propuestas-evaluadas.txt` | Propuestas de arquitectura evaluadas y descartadas |

## Cómo agregar una sesión nueva

1. Copia el intercambio relevante (prompt + respuesta) a un archivo nuevo aquí.
2. Agrega una fila al índice de arriba.
3. Si la sesión se usó para el proyecto, referencia también el commit donde
   se incorporó (ej. "ver commit `abc1234`").

No hace falta capturar cada mensaje de cada conversación -- el objetivo es
mostrar evidencia real de uso de IA en decisiones concretas, no un archivo
por cada intercambio trivial.
