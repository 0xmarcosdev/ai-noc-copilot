# Resumen de builds — Fases A y B del dashboard

> Documento de sesión: consolida todo lo implementado en las dos primeras
> fases del plan de mejoras gráficas (`docs/recomendaciones_dashboard.txt`
> + `docs/branding.md` + `docs/isotype.md`). Sirve como evidencia para el
> DEVLOG y como guía de verificación manual.
>
> Fecha: 21 ago 2026 · Asistente: OpenCode (ox-alpha) en modo Build
> Estado: tests 23/23 en verde, ruff limpio, validado en vivo

---

## Contexto previo

El plan completo de mejoras gráficas se organizó en 4 fases secuenciales:

| Fase | Alcance | Estado |
|---|---|---|
| **A — Fundamentos visuales + UX de bajo riesgo** | CSS de marca, isotipo, favicon, badges, refresh, paginación, tiempo IA, help de filtro | ✅ Esta entrega |
| **B — Filtros avanzados** | Fecha/hora, rango de ID, sort por campo (backend + frontend) | ✅ Esta entrega |
| C — Persistencia de correlación | Guardar grupos detectados en BD, historial, distinción bruteforce/portscan | ⬜ Siguiente |
| D — Estadísticas y gráficos | Panel enriquecido, Plotly offline, export CSV/JSON | ⬜ Pendiente |

Restricciones respetadas (SPEC §11): sin dependencias cloud ni CDNs
(air-gapped), contrato del LLM intacto, plataforma Windows, copy en español,
`backend/app/main.py` tocado solo en Fase B con params opcionales que no
rompen el contrato `{total, limit, offset, items}` de SPEC §5.

---

## Fase A — Fundamentos visuales + UX de bajo riesgo

### Objetivo
Alinear el dashboard con la identidad visual de `docs/branding.md` e
`docs/isotype.md` y resolver los puntos de UX de bajo riesgo de
`recomendaciones_dashboard.txt`, sin tocar lógica de negocio.

### Tareas implementadas

1. **CSS de marca inyectado** (`frontend/dashboard.py`)
   - Bloque `<style>` con variables `--ainoc-*` tomadas textualmente de
     `branding.md` §7: `bg #0B1220`, `panel #111827`, `elevated #1F2937`,
     `border #374151`, `accent #22D3EE`, `accent-dim #0891B2`,
     `text #F3F4F6`, `muted #9CA3AF`, severidades `high #F43F5E` /
     `medium #F59E0B` / `low #34D399`.
   - Aplicado a `.stApp`, sidebar, expanders (panel + borde redondeado),
     botones `kind="primary"` (acento cian con hover `accent-dim`) y labels
     de inputs. Sin colores inventados.

2. **Header con isotipo animado** (reemplaza `st.title("🛰️ ...")`)
   - SVG inline del radar (anillo + anillo interior tenue + nodo central +
     3 blips + barrido), sección "SVG + animación CSS solo con transform"
     de `isotype.md`.
   - Animación solo con `transform`/`opacity` (GPU-friendly): rotación del
     barrido a 3 s por vuelta, pulso de blips cada 2,4 s con desfases de
     0,8 s; `will-change` acotado al grupo del barrido.
   - `@media (prefers-reduced-motion: reduce)` desactiva toda animación.
   - Título "AI-NOC Copilot" + tagline oficial "Copiloto local de logs de
     pfSense — 100 % offline" vía `st.markdown(unsafe_allow_html=True)`.

3. **Favicon estático** (`frontend/static/favicon.svg`, archivo nuevo)
   - Versión mínima 32×32 de `isotype.md`: rect redondeado `#0B1220`,
     anillo cian, nodo y un blip. Sin animación (los favicons no animan de
     forma fiable).
   - Registrado en `st.set_page_config(page_icon="static/favicon.svg")`.

4. **Badge de severidad + indicador analyzed/unanalyzed** por evento
   - Pastilla HTML inline en el label del expander con el color exacto de
     `branding.md` §4 según la severidad del evento (fondo semitransparente
     descartado en favor de fondo sólido + texto blanco, legible sobre
     panel oscuro).
   - Indicador de estado: 🟢 analizado / ⚪ sin analizar (recomendación #11).

5. **Botón "🔄 Actualizar"** (recomendación #1)
   - Al pulsarlo guarda el total actual en
     `st.session_state.refrescar_total_anterior`, hace `st.rerun()` y, tras
     recargar, compara contra el nuevo total mostrando
     `st.toast("N eventos nuevos")` o `"N eventos quitados"`.

6. **Tiempo de respuesta del LLM** (recomendación #9)
   - "Explicar con IA" mide con `time.perf_counter()` alrededor del POST y
     muestra `st.caption("⏱️ X.XXs")` junto a la explicación.

7. **Paginación rediseñada** (recomendación #4)
   - « Primera · input "Ir a página" (con clamp a rango válido) · ‹ Anterior ·
     info "Mostrando A–B de TOTAL · página N/M" · Siguiente › · Última ».
   - Sin cambios de backend: usa `total`/`limit`/`offset` ya existentes.

8. **Filtro "Tipo de evento (parcial)"** (recomendación #3)
   - Mantenido como `text_input` con `help="Escribí parte del tipo, ej:
     'fuerza bruta'"`. La conversión a selectbox dinámico queda para fase B+
     según lo acordado.

9. **Punto 8 (copiar al portapapeles)**: verificado que la versión instalada
   de Streamlit ya muestra botón de copiar nativo en `st.code()` → no se
   construyó nada extra.

### Bug corregido durante la fase (post-entrega)
- La primera versión de la paginación tenía `pcol5.button("→")` llamado dos
  veces con el mismo label sin `key` explícito → `DuplicateWidgetID` en
  runtime. Detectado al pasar ruff (PIE804/SIM102) y reescrita completa con
  columnas dedicadas por botón e input con clave fija `go_to_page`.
- `page_icon` apuntaba a `"favicon.svg"` (raíz) pero el archivo vive en
  `static/`; corregido a `"static/favicon.svg"` antes de la validación en vivo.

---

## Fase B — Filtros avanzados (fecha/hora, rango de ID, orden)

### Objetivo
Resolver recomendaciones #2 (ID visible + filtro por ID/rango), #7 (sort) y
#8 (filtro por fecha y hora) extendiendo `GET /events` **sin romper el
contrato existente** y conectando los nuevos controles en el dashboard.

### Backend — `backend/app/main.py`

Nuevos parámetros opcionales en `GET /events` (defaults = comportamiento
original, `received_at desc`):

| Parámetro | Tipo | Semántica |
|---|---|---|
| `id_from` / `id_to` | int? | Rango cerrado `id >= from AND id <= to`. Invertido → resultado vacío (el dashboard lo intercambia antes de enviar). |
| `received_at_from` / `received_at_to` | datetime? | Ventana de ingesta, datetimes naive UTC (decisión documentada del proyecto). |
| `sort_by` | Literal | `id` \| `received_at` \| `severity` \| `event_type`. Valor inválido → 422 automático (validación FastAPI). |
| `sort_dir` | Literal | `asc` \| `desc`. |

Detalles de diseño:
- Se añadió `NetworkEvent.id` como **desempate del ORDER BY**: paginación
  determinista cuando hay timestamps idénticos (caso típico tras ingesta
  manual, donde todas las líneas reciben `utcnow()`).
- `sort_by`/`sort_dir` con `typing.Literal`: la validación de contrato vive
  en la firma del endpoint, consistente con la política de errores de SPEC §5.
- No se tocó ningún otro endpoint; el JSON de respuesta no cambia de forma.

### Frontend — `frontend/dashboard.py`

- Expander **"🗓️ Filtros de fecha y ID"**: `date_input` desde/hasta +
  `time_input` hora desde/hasta (por defecto vacíos = sin filtro); IDs como
  `text_input` con parseo seguro (`_parse_id`, no numérico → None).
- Rango de ID invertido se intercambia silenciosamente en cliente.
- Selects **"Ordenar por"** / **"Dirección"** mapeados a los valores del API
  vía dict `SORT_FIELDS` (única fuente de verdad en el frontend).
- Todos los filtros nuevos integrados en `filter_state`: cambiar cualquiera
  resetea la paginación a la página 1 (patrón ya existente).
- Label de cada evento ahora arranca con `[#{id}]` (recomendación #2,
  mitad "mostrar el ID de forma precisa").

### Documentación — `docs/SPEC.md`

§5 actualizado: fila de la tabla de API con la querystring completa y
párrafo de filtros ampliado (rangos, ventana temporal, orden, 422 en
valores inválidos, desempate por id). Pie de archivo con nota de la
actualización. Regla de AGENTS.md: SPEC viaja junto con cambios de contrato.

---

## Verificación (triple check)

1. **Tests**: `pytest tests -v` desde `backend/` → **23/23 PASSED**
   (20 previos + 3 nuevos):
   - `test_list_events_id_range_filter` — rango parcial, ID único cerrado,
     rango invertido → total 0.
   - `test_list_events_date_range_filter` — ventana [-7d, -3d] que captura
     solo el evento insertado a -5 días; límite inferior suelto incluye el
     futuro y excluye el viejo.
   - `test_list_events_sort_params` — asc/desc por id, orden alfabético por
     severity (`high < low < medium`), y `sort_by=raw_message` /
     `sort_dir=lateral` → 422.
2. **Lint**: `ruff check app tests ../frontend` → All checks passed
   (line-length 110, DTZ ignorados por decisión documentada).
3. **Sintaxis frontend**: `python -m py_compile dashboard.py` → OK.
4. **Validación en vivo** (ver comandos abajo): backend arriba en :8000,
   ingesta de líneas de prueba, respuestas correctas de `/events` con
   `sort_by=id&sort_dir=asc`, `id_from/id_to` y `received_at_from`;
   dashboard sirviendo en :8501.

### Comandos de validación manual (Windows)

```powershell
# Backend
cd D:\AiProject\ai-noc-copilot\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (en otra terminal; usa el MISMO venv del backend)
cd D:\AiProject\ai-noc-copilot\frontend
D:\AiProject\ai-noc-copilot\backend\.venv\Scripts\streamlit.exe run dashboard.py --server.port 8501 --server.headless true

# Pruebas rápidas del nuevo contrato
curl.exe "http://localhost:8000/events?limit=3&sort_by=id&sort_dir=asc"
curl.exe "http://localhost:8000/events?id_from=1&id_to=5"
curl.exe "http://localhost:8000/events?received_at_from=2026-08-01T00:00:00"
```

En el navegador: abrir http://localhost:8501 y verificar — header animado
(respetando reduced-motion del SO), paleta oscura de marca, badge de
severidad por fila, `[#{id}]` en cada label, expander de filtros avanzados,
orden funcional y toast del botón Actualizar.

---

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `frontend/dashboard.py` | Fases A+B completas (visual + filtros) |
| `frontend/static/favicon.svg` | Nuevo (Fase A) |
| `backend/app/main.py` | Params nuevos en `GET /events` (Fase B) |
| `backend/tests/test_api.py` | +3 tests (Fase B) |
| `docs/SPEC.md` | §5 y pie actualizados (Fase B) |
| `docs/resumen-fases-a-b-dashboard.md` | Este documento |

Pendiente de decisión del humano (no commiteado por no ser de estas fases):
`ROADMAP.md` tenía un cambio preexistente (swap de estado Fase 5.6/5.7),
export `visual_identity_session-ses_fe00.md` en raíz y notas en
`docs/ai-sessions/`.

---

## Qué sigue — Fase C (preview)

Persistencia de correlación (recomendación #5, "es muy importante"):
modelo `CorrelationGroup` en SQLite + guardado dentro de `POST
/events/correlate` + endpoint de historial + sección UI. Incluye la
distinción bruteforce vs portscan (#6) pasando el patrón de puertos al
prompt de correlación, y el reporte on-demand (#12) si queda espacio de
sesión. Requiere migración de esquema aditiva (nueva tabla, sin tocar
`NetworkEvent`) — compatible con `SQLModel.metadata.create_all`.
