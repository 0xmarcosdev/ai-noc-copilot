# Sesión 13 — 24 ago 2026 — Verificación final y guion de demo

## Contexto

El proyecto está en fase de cierre para la entrega del 4 de septiembre 2026.
Las Fases 0–5.9 están funcionalmente completas. Esta sesión se enfocó en:
verificar que no quedan dependencias innecesarias (pandas), escribir el
guion de demo para la grabación, y correr la regresión final completa.

## Participantes

- **Humano**: dirección técnica, decisiones de diseño
- **OpenCode (Mimo v2.5-free)**: implementación, verificación, documentación

## Decisiones tomadas

### 1. No se necesita pandas para exportar CSV/JSON

**Contexto**: El dashboard.py usa `csv.DictWriter`, `json.dumps` e
`io.StringIO` del estándar de Python para generar archivos CSV y JSON
descargables. No se usa `pandas` en ningún punto del frontend.

**Verificación**: se leyeron las primeras 50 líneas de `dashboard.py` y se
confirmó que solo importa `csv`, `json`, `io` (stdlib) + `streamlit`,
`httpx`, `plotly`.

**Decisión**: no tocar `frontend/requirements.txt` ni `frontend/Dockerfile`.
La dependencia de pandas no existe y no hay que crearla.

### 2. Guion de demo: secuencia de 8 escenas, 8–10 minutos

Se creó `docs/demo-script.md` con:
- **Checklist pre-grabación**: 7 ítems para verificar antes de grabar
  (Ollama, backend, frontend, DB limpia, etc.)
- **8 escenas paso a paso** con comandos exactos, resultados esperados
  y qué explicar en cada momento
- **Notas técnicas**: tiempos del LLM, limpieza de DB, recordatorio de
  hacer click en "Correlacionar"

La demo sigue la narrativa de "evento aislado = low, grupo correlacionado = high"
que es el punto más fuerte del proyecto.

### 3. ROADMAP actualizado

- Fase 5.8: ítem del dashboard de histórico marcado como completado
  (ya estaba hecho desde la sesión anterior pero el ROADMAP no lo reflejaba
  correctamente)
- Fase 6: marcados los ítems de README y SPEC.md como completados,
  annotados los que dependen del humano (evidencia de IA, Docker,
  grabación, ensayo)

## Estado de verificación

| Verificación | Estado |
|---|---|
| pytest (31/31 tests) | ✅ |
| ruff check (backend + frontend) | ✅ |
| py_compile main.py | ✅ |
| py_compile test_api.py | ✅ |
| py_compile dashboard.py | ✅ |
| stdlib csv/json (sin pandas) | ✅ confirmado |

## Archivos creados o modificados

| Archivo | Acción |
|---|---|
| `docs/demo-script.md` | **Creado** — guion de demo + checklist pre-grabación |
| `ROADMAP.md` | **Modificado** — Fase 5.8 completada, Fase 6 annotada |

## Pendiente para humano

1. Grabar la demo siguiendo el guion en `docs/demo-script.md`
2. Probar `docker compose up` de punta a punta (requiere Docker + Ollama en 0.0.0.0:11434)
3. Exportar evidencia de uso de IA (esta sesión + las anteriores)
4. Ensayar la presentación cronometrada
