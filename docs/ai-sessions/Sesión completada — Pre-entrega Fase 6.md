###✅ Sesión completada — Pre-entrega Fase 6

Resumen de cambios
PARTE 0 — Correcciones pendientes:
- frontend/requirements.txt creado con streamlit, httpx, plotly pineados
- frontend/Dockerfile actualizado para usar requirements.txt en vez de pip install suelto
- README.md Opción A actualizada para usar frontend/requirements.txt
- _severity_badge: confirmado que hay UNA sola función, no duplicación (error tipográfico en reporte anterior)
PARTE 1 — Inspección Docker:
- docs/docker-validation.md creado con análisis completo:
- Backend: todos los imports cruzados contra requirements.txt ✅
- Frontend: todos los imports cruzados contra requirements.txt ✅
- Variables de entorno: todas con default razonable o en compose ✅
- Healthcheck: apunta a /health que existe ✅
- .dockerignore: excluye .venv, data, tests correctamente ✅
PARTE 2 — README:
- Sección de arquitectura: agregados endpoints detect-beaconing, detect-suspicious-dns, GET /summary
- Frontend: documentadas features de Fases 5.8/5.9 (histórico correlación, gráficos plotly, exportar CSV/JSON, reporte on-demand)
- Escenarios de prueba: agregados beacon, dns_dga, dns_normal, vpn_flapping; cambiado bash a powershell
- Corregido "el build falla" → "docker compose up falla"
PARTE 3 — SPEC.md:
- §2: "Correlación básica (en progreso)" → "Correlación de eventos" (ya completada)
- Pie: actualizado con cambios de esta sesión
PARTE 4 — Evidencia de IA:
- docs/ai-sessions/README.md actualizado: 12 sesiones indexadas (vs 6 antes), columna "Fase" agregada, documentos de diseño listados
Verificación final
- ✅ 31/31 tests pasando
- ✅ ruff check limpio (backend + frontend)
- ✅ py_compile dashboard.py OK
- ✅ ROADMAP.md refleja estado real (Fases 5.8/5.9 completas, Fase 6 pendiente)
Propuesta de commits
PARTE 0:
fix: frontend/requirements.txt y Dockerfile — plotly incluido

Crea frontend/requirements.txt con streamlit, httpx y plotly pineados.
Actualiza frontend/Dockerfile para usar requirements.txt en vez de
pip install suelto. Corrige la omisión de plotly que rompía docker
compose up (el contenedor del frontend no tenía plotly instalado).
PARTE 1+3 (docs juntas):
docs: inspección Docker y última pasada de SPEC.md

Agrega docs/docker-validation.md con inspección estática completa
(imports, env vars, healthcheck, .dockerignore). Corrige SPEC §2
(correlación completada, no "en progreso"). Actualiza pie de SPEC.
PARTE 2:
docs: README actualizado con features de Fases 5.8/5.9

Agrega al README: endpoints detect-beaconing, detect-suspicious-dns,
GET /summary; features del frontend (histórico correlación, gráficos
plotly, exportar CSV/JSON, reporte on-demand); escenarios sintéticos
completos; corrige sintaxis y terminología de Docker.
PARTE 4:
docs: índice de evidencia de IA actualizado

Actualiza docs/ai-sessions/README.md con 12 sesiones indexadas
(vs 6 anteriormente), columna de fase, y listado de documentos
de diseño visual.
