import os
from datetime import datetime, time

import httpx
import streamlit as st

# ⚠️ REGLA DE STREAMLIT: st.set_page_config DEBE ser la primera llamada a 'st.' en el script
st.set_page_config(page_title="AI-NOC Copilot", layout="wide", page_icon="static/favicon.svg")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Campos por los que se puede ordenar GET /events (contrato backend, SPEC §5)
SORT_FIELDS = {
    "Fecha de recepción": "received_at",
    "ID": "id",
    "Severidad": "severity",
    "Tipo de evento": "event_type",
}


def _parse_id(texto: str) -> int | None:
    """Convierte texto a ID entero; vacío o no numérico -> None (sin filtro)."""
    texto = texto.strip()
    return int(texto) if texto.isdigit() else None


# CSS de marca inyectado (docs/branding.md §7) - FASE A
BRANDING_CSS = """
<style>
    :root {
        --ainoc-bg: #0B1220;
        --ainoc-panel: #111827;
        --ainoc-elevated: #1F2937;
        --ainoc-border: #374151;
        --ainoc-accent: #22D3EE;
        --ainoc-accent-dim: #0891B2;
        --ainoc-text: #F3F4F6;
        --ainoc-muted: #9CA3AF;
    }
    .stApp { background-color: var(--ainoc-bg) !important; color: var(--ainoc-text) !important; }
    section[data-testid="stSidebar"] { background-color: var(--ainoc-panel) !important; border-right: 1px solid var(--ainoc-border) !important; }
    .stExpander { background-color: var(--ainoc-panel) !important; border: 1px solid var(--ainoc-border) !important; border-radius: 8px !important; }
    .stExpander .streamlit-expanderHeader { color: var(--ainoc-text) !important; }
    div[data-baseweb="button"] > button[kind="primary"] { 
        background-color: var(--ainoc-accent) !important; 
        color: var(--ainoc-bg) !important; 
        font-weight: 600 !important;
        border: none !important;
    }
    div[data-baseweb="button"] > button[kind="primary"]:hover { 
        background-color: var(--ainoc-accent-dim) !important; 
    }
    .stTextInput input, .stSelectbox select, .stNumberInput input, .stDateInput input, .stTimeInput input {
        background-color: var(--ainoc-elevated) !important;
        color: var(--ainoc-text) !important;
        border: 1px solid var(--ainoc-border) !important;
    }
    label { color: var(--ainoc-muted) !important; }
</style>
"""
st.markdown(BRANDING_CSS, unsafe_allow_html=True)

# Isotipo animado SVG + CSS (docs/isotype.md) - FASE A
AINOC_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="40" height="40" role="img" aria-label="AI-NOC Copilot">
  <defs>
    <style>
      .ring{fill:none;stroke:#22D3EE;stroke-width:2.25;stroke-linecap:round}
      .ring-dim{fill:none;stroke:#22D3EE;stroke-width:1.25;opacity:.35}
      .node,.blip{fill:#22D3EE}
      .sweep-line{fill:none;stroke:#22D3EE;stroke-width:1.75;stroke-linecap:round;opacity:.9}
      .sweep-wedge{fill:#22D3EE;opacity:.14}
      .sweep-group{transform-origin:0px 0px;transform:translateZ(0);backface-visibility:hidden;animation:ainoc-sweep 3s linear infinite;will-change:transform}
      .blip{animation:ainoc-pulse 2.4s ease-in-out infinite;will-change:opacity}
      .blip-b{animation-delay:.8s}.blip-c{animation-delay:1.6s}
      @keyframes ainoc-sweep{from{transform:translateZ(0) rotate(0deg)}to{transform:translateZ(0) rotate(360deg)}}
      @keyframes ainoc-pulse{0%,100%{opacity:1}50%{opacity:.35}}
      @media (prefers-reduced-motion:reduce){.sweep-group,.blip{animation:none!important;will-change:auto}}
    </style>
  </defs>
  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>
  <g transform="translate(32 32)"><g class="sweep-group">
    <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
    <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
  </g></g>
  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip blip-b" cx="18" cy="46" r="1.7"/>
  <circle class="blip blip-c" cx="42" cy="48.5" r="1.5"/>
</svg>"""

# Header con isotipo animado + título + tagline
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:0.75rem;">
      <div style="flex-shrink:0;width:40px;height:40px;">{AINOC_LOGO_SVG}</div>
      <div>
        <div style="font-size:1.5rem;font-weight:600;color:#F3F4F6;line-height:1.2;">AI-NOC Copilot</div>
        <div style="color:#9CA3AF;font-size:0.9rem;">Copiloto local de logs de pfSense — 100 % offline</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Notificaciones persistentes desde session_state (FIX: ingest y actualizar)
if "notification" in st.session_state:
    notif = st.session_state.notification
    if notif["type"] == "success":
        st.success(notif["message"], icon="✅")
    elif notif["type"] == "error":
        st.error(notif["message"], icon="❌")
    elif notif["type"] == "info":
        st.info(notif["message"], icon="ℹ️")
    # Limpiar notificación después de mostrarla
    del st.session_state.notification

# Botón refrescar: guarda total anterior en session_state, luego hace rerun
# y compara el total nuevo contra el anterior
if "refrescar_total_anterior" not in st.session_state:
    st.session_state.refrescar_total_anterior = None

if st.button(" Actualizar", key="refresh_btn"):
    st.session_state.refrescar_total_anterior = st.session_state.get("total_cargado", 0)
    st.rerun()

# Después del rerun, comparar total anterior vs nuevo
if st.session_state.get("refrescar_total_anterior") is not None:
    anterior = st.session_state.refrescar_total_anterior
    nuevo = st.session_state.get("total_cargado", 0)
    if nuevo != anterior:
        diff = nuevo - anterior
        msg = f"📊 {diff} eventos nuevos" if diff > 0 else f"📉 {abs(diff)} eventos eliminados"
        st.session_state.notification = {"type": "info", "message": msg}
        st.rerun()  # Segundo rerun para mostrar la notificación
    st.session_state.refrescar_total_anterior = None

with st.expander("📥 Ingesta manual de logs"):
    pasted = st.text_area(
        "Pegar logs (una línea por evento)",
        height=160,
        placeholder="Aug 19 12:00:00 pfsense-prod filterlog: ...",
    )
    uploaded = st.file_uploader("...o subir un archivo de log", type=["log", "txt"])
    if st.button("Ingerir logs", type="primary"):
        content = None
        if uploaded is not None:
            content = uploaded.getvalue().decode("utf-8", errors="replace")
        elif pasted.strip():
            content = pasted
        if content:
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/events/ingest",
                    json={"content": content},
                    timeout=30,
                    trust_env=False,
                )
                resp.raise_for_status()
                data = resp.json()
                # FIX: Guardar notificación en session_state antes del rerun
                st.session_state.notification = {
                    "type": "success",
                    "message": f"✅ {data['ingested']} eventos ingeridos correctamente",
                }
                st.rerun()
            except httpx.HTTPError as exc:
                st.session_state.notification = {"type": "error", "message": f"❌ Error al ingerir: {exc}"}
                st.rerun()
        else:
            st.warning("Pegá logs o subí un archivo primero.")
    st.caption("Recordá sanitizar IPs internas antes de pegar logs reales (ver SPEC §8).")

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("Resumen")
    summary_data = None
    try:
        summary_data = httpx.get(f"{BACKEND_URL}/summary", timeout=5, trust_env=False).json()
        st.metric("Eventos analizados", summary_data["total_analyzed"])
        for sev, count in summary_data.get("by_severity", {}).items():
            st.write(f"**{sev}**: {count}")
    except httpx.HTTPError:
        st.warning("No se pudo conectar al backend.")

    top_types = (summary_data or {}).get("top_high_severity_types", [])
    if top_types:
        st.markdown("**Tipos dominantes en alertas altas:**")
        for item in top_types:
            st.write(f"- {item['event_type']}: {item['count']}")

    st.divider()
    st.subheader("🔗 Correlación de eventos")
    if st.button("Correlacionar eventos sin analizar"):
        with st.spinner("Buscando patrones..."):
            correlation = None
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/events/correlate",
                    params={"window_minutes": 10, "threshold": 5},
                    timeout=90,
                    trust_env=False,
                )
                resp.raise_for_status()
                correlation = resp.json()
            except httpx.HTTPError as exc:
                st.error(f"Error al correlacionar: {exc}")

        if correlation:
            if correlation["groups_detected"] == 0:
                st.info("No se detectaron patrones que superen el umbral.")
            else:
                st.success(f"{correlation['groups_detected']} patrón(es) detectado(s)")
                for group in correlation["groups"]:
                    icon = "🚨" if group["severity"] == "high" else "⚠️"
                    label = f"{icon} {group['attacker_ip']} — {group['event_type']} ({group['event_count']} eventos)"
                    with st.expander(label):
                        st.markdown(f"**Severidad:** `{group['severity']}`")
                        st.markdown(f"**Explicación:** {group['explanation']}")
                        st.markdown(f"**Acción recomendada:** {group['recommended_action']}")
                        st.caption(f"IDs de eventos: {', '.join(map(str, group['event_ids']))}")

with col1:
    st.subheader("Eventos recientes")
    only_new = st.checkbox("Solo sin analizar", value=False)
    search_q = st.text_input("Buscar en raw_message", placeholder="ej: 203.0.113.99")
    fcol1, fcol2 = st.columns(2)
    sev_filter = fcol1.selectbox(
        "Severidad",
        ["", "low", "medium", "high"],
        format_func=lambda s: "Todas" if s == "" else s,
    )
    type_filter = fcol2.text_input(
        "Tipo de evento (parcial)",
        help="Escribí parte del tipo, ej: 'fuerza bruta'",
    )

    # Filtros avanzados: ventana de fecha/hora y rango de IDs (FASE B)
    with st.expander("🗓️ Filtros de fecha y ID"):
        dcol1, dcol2 = st.columns(2)
        date_from = dcol1.date_input("Desde", value=None, format="DD/MM/YYYY")
        time_from = dcol1.time_input("Hora desde", value=None)
        date_to = dcol2.date_input("Hasta", value=None, format="DD/MM/YYYY")
        time_to = dcol2.time_input("Hora hasta", value=None)

        icol1, icol2 = st.columns(2)
        id_from_raw = icol1.text_input("ID desde", placeholder="ej: 10")
        id_to_raw = icol2.text_input("ID hasta", placeholder="ej: 50")

    # Ordenación por campo (FASE B)
    scol1, scol2 = st.columns([3, 2])
    sort_label = scol1.selectbox("Ordenar por", list(SORT_FIELDS.keys()))
    sort_dir_label = scol2.selectbox("Dirección", ["Descendente ↓", "Ascendente ↑"])

    page_size = st.selectbox("Por página", [10, 25, 50], index=1)
    filter_state = (
        only_new,
        search_q,
        sev_filter,
        type_filter,
        page_size,
        str(date_from),
        str(time_from),
        str(date_to),
        str(time_to),
        id_from_raw,
        id_to_raw,
        sort_label,
        sort_dir_label,
    )
    if st.session_state.get("events_filters") != filter_state:
        st.session_state["events_page"] = 0
        st.session_state["events_filters"] = filter_state
    page = st.session_state.get("events_page", 0)

    # Armar parámetros de filtros avanzados
    received_from = datetime.combine(date_from, time_from or time.min) if date_from else None
    received_to = datetime.combine(date_to, time_to or time(23, 59, 59)) if date_to else None
    id_from_val = _parse_id(id_from_raw)
    id_to_val = _parse_id(id_to_raw)
    if id_from_val is not None and id_to_val is not None and id_from_val > id_to_val:
        id_from_val, id_to_val = id_to_val, id_from_val

    try:
        raw_params = {
            "only_unanalyzed": only_new,
            "q": search_q or None,
            "severity": sev_filter or None,
            "event_type": type_filter or None,
            "id_from": id_from_val,
            "id_to": id_to_val,
            "received_at_from": received_from.isoformat() if received_from else None,
            "received_at_to": received_to.isoformat() if received_to else None,
            "sort_by": SORT_FIELDS[sort_label],
            "sort_dir": "asc" if "Asc" in sort_dir_label else "desc",
            "limit": page_size,
            "offset": page * page_size,
        }
        params = {k: v for k, v in raw_params.items() if v is not None}
        resp = httpx.get(
            f"{BACKEND_URL}/events",
            params=params,
            timeout=5,
            trust_env=False,
        )
        payload = resp.json()
        if resp.status_code >= 400 or "items" not in payload:
            st.warning(f"El backend respondió {resp.status_code} — revisá los filtros.")
            events, total = [], 0
        else:
            events = payload["items"]
            total = payload["total"]

        # FIX: Guardar el total actual para que el botón "Actualizar" funcione
        st.session_state["total_cargado"] = total

    except httpx.HTTPError:
        events = []
        total = 0
        st.session_state["total_cargado"] = 0
        st.error("Backend no disponible. ¿Corriste el backend?")

    if not events:
        st.info("No hay eventos que coincidan con los filtros.")

    for event in events:
        # 1. Formatear timestamp para que sea legible (ej: "23/08 00:33")
        received_dt = event["received_at"]
        if isinstance(received_dt, str):
            from datetime import datetime

            received_dt = datetime.fromisoformat(received_dt.replace("Z", "+00:00"))
        timestamp_fmt = received_dt.strftime("%d/%m %H:%M")

        # 2. Un solo indicador de estado (combina severidad + análisis)
        sev = event.get("severity", "")
        analyzed = event.get("analyzed", False)

        if analyzed:
            status_emoji = {"high": "🔴✓", "medium": "🟠✓", "low": "🟢✓"}.get(sev, "⚪✓")
        else:
            status_emoji = "⚪"

        event_type = event.get("event_type") or "sin analizar"
        source_ip = event["source_ip"]

        # 3. Label limpio y digerible
        label = f"[#{event['id']}] [{timestamp_fmt}] {source_ip} — {event_type} {status_emoji}"

        with st.expander(label):
            st.code(event["raw_message"], language="text")
            if event.get("analyzed"):
                st.markdown(f"**Severidad:** `{event['severity']}`")
                st.markdown(f"**Explicación IA:** {event['ai_explanation']}")

                # Mostrar tiempo de respuesta (ahora debería ser < 5s)
                time_key = f"analysis_time_{event['id']}"
                if time_key in st.session_state:
                    elapsed = st.session_state[time_key]
                    st.caption(f"⏱️ {elapsed:.2f}s")
            else:
                if st.button("Explicar con IA", key=f"analyze-{event['id']}"):
                    with st.spinner("🔄 Consultando al modelo local..."):
                        import time

                        start = time.perf_counter()
                        try:
                            resp = httpx.post(
                                f"{BACKEND_URL}/events/{event['id']}/analyze",
                                timeout=30,  # 30s es más que suficiente ahora que no hay bug de IPv6
                                trust_env=False,
                            )
                            elapsed = time.perf_counter() - start

                            if resp.status_code == 200:
                                st.session_state[f"analysis_time_{event['id']}"] = elapsed
                                st.rerun()
                            else:
                                st.error(f"Error del backend: {resp.text}")
                        except httpx.ConnectError:
                            st.error("❌ No se pudo conectar a Ollama. Ejecutá `scripts\\ensure_ollama.bat`")
                        except httpx.TimeoutException:
                            st.error("⏰ Timeout. El modelo tardó más de 30s en responder.")

    # Paginación rediseñada (FASE A)
    total_pages = max(1, (total + page_size - 1) // page_size)
    prev_disabled = page == 0
    next_disabled = (page + 1) * page_size >= total

    pcol_first, pcol_input, pcol_prev, pcol_info, pcol_next, pcol_last = st.columns(
        [1.2, 0.9, 1.2, 2.2, 1.2, 1.2]
    )

    def _ir_a_pagina() -> None:
        valor = st.session_state.get("go_to_page", "")
        if valor.isdigit():
            destino = max(1, min(int(valor), total_pages)) - 1
            st.session_state["events_page"] = destino

    if pcol_first.button("« Primera", disabled=prev_disabled, help="Ir a la primera página"):
        st.session_state["events_page"] = 0
        st.rerun()

    pcol_input.text_input(
        "Página",
        value=str(page + 1),
        max_chars=4,
        key="go_to_page",
        on_change=_ir_a_pagina,
        label_visibility="collapsed",
    )

    if pcol_prev.button("‹ Anterior", disabled=prev_disabled):
        st.session_state["events_page"] = max(0, page - 1)
        st.rerun()

    desde = (page * page_size) + 1
    hasta = min((page + 1) * page_size, total)
    pcol_info.markdown(f"Mostrando {desde}–{hasta} de {total} · página {page + 1}/{total_pages}")

    if pcol_next.button("Siguiente ›", disabled=next_disabled):
        st.session_state["events_page"] = page + 1
        st.rerun()

    if pcol_last.button("Última »", disabled=(page >= total_pages - 1), help="Ir a la última página"):
        st.session_state["events_page"] = total_pages - 1
        st.rerun()
