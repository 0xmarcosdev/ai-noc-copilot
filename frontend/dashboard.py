import csv
import io
import json
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


SEVERITY_COLORS = {"high": "🔴", "medium": "🟠", "low": "🟢"}
SEVERITY_HEX = {"high": "#EF4444", "medium": "#F59E0B", "low": "#22C55E"}
PATTERN_ICONS = {"fuerza_bruta": "🎯", "escaneo_puertos": "📡"}


def _severity_badge(severity: str | None, analyzed: bool = True) -> str:
    """Retorna un emoji de severidad consistente con el resto del dashboard."""
    sev = severity or "low"
    icon = SEVERITY_COLORS.get(sev, "⚪")
    return f"{icon}✓" if analyzed else icon


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
    /* Chat section */
    .ainoc-chat-header{display:flex;align-items:center;gap:8px;padding:0.5rem 0;margin-bottom:0.25rem}
    .ainoc-chat-header h3{margin:0;font-size:1.1rem}
    .ainoc-chat-help{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:#374151;color:#9CA3AF;font-size:11px;cursor:help;position:relative;border:none;padding:0;line-height:1}
    .ainoc-chat-help:hover{background:#4B5563;color:#F3F4F6}
    .ainoc-chat-help .ainoc-chat-tooltip{display:none;position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);background:#1F2937;color:#F3F4F6;padding:8px 12px;border-radius:8px;font-size:12px;white-space:nowrap;z-index:999;box-shadow:0 4px 12px rgba(0,0,0,.4);line-height:1.5;border:1px solid #374151}
    .ainoc-chat-help:hover .ainoc-chat-tooltip{display:block}
    .ainoc-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0.4rem 0}
    .ainoc-chip{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:16px;border:1px solid #374151;background:#1F2937;color:#D1D5DB;font-size:12px;cursor:pointer;transition:all .15s ease;white-space:nowrap;line-height:1.4}
    .ainoc-chip:hover{background:#22D3EE;color:#0B1220;border-color:#22D3EE}
    .ainoc-msg-user{background:#22D3EE;color:#0B1220;padding:10px 14px;border-radius:16px 16px 4px 16px;max-width:82%;margin-left:auto;font-size:.9rem;line-height:1.5}
    .ainoc-msg-ai{background:#1F2937;color:#F3F4F6;padding:10px 14px;border-radius:16px 16px 16px 4px;max-width:82%;border:1px solid #374151;font-size:.9rem;line-height:1.5}
    .stChatMessage{background:transparent !important;padding:4px 0 !important}
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
    del st.session_state.notification

# Botón refrescar
if "refrescar_total_anterior" not in st.session_state:
    st.session_state.refrescar_total_anterior = None

if st.button(" Actualizar", key="refresh_btn"):
    st.session_state.refrescar_total_anterior = st.session_state.get("total_cargado", 0)
    st.rerun()

if st.session_state.get("refrescar_total_anterior") is not None:
    anterior = st.session_state.refrescar_total_anterior
    nuevo = st.session_state.get("total_cargado", 0)
    if nuevo != anterior:
        diff = nuevo - anterior
        msg = f"📊 {diff} eventos nuevos" if diff > 0 else f"📉 {abs(diff)} eventos eliminados"
        st.session_state.notification = {"type": "info", "message": msg}
        st.rerun()
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
    st.subheader("📊 Resumen")
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

    # --- GRÁFICOS (Fase 5.9, recomendación #10) ---
    st.subheader("📈 Gráficos")
    if summary_data:
        import plotly.graph_objects as go

        # Gráfico 1: Distribución por severidad (pie chart)
        by_sev = summary_data.get("by_severity", {})
        if by_sev:
            labels = list(by_sev.keys())
            values = list(by_sev.values())
            colors = [SEVERITY_HEX.get(s, "#6B7280") for s in labels]
            fig_sev = go.Figure(data=[go.Pie(
                labels=labels, values=values,
                marker={"colors": colors},
                hole=0.4,
                textinfo="label+value",
            )])
            fig_sev.update_layout(
                title_text="Severidad",
                height=280,
                margin={"t": 40, "b": 20, "l": 20, "r": 20},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#F3F4F6"},
                showlegend=False,
            )
            st.plotly_chart(fig_sev, use_container_width=True)

        # Gráfico 2: Distribución por tipo de evento (barras)
        by_type = summary_data.get("by_event_type", [])
        if by_type:
            type_labels = [t["event_type"] for t in by_type[:10]]
            type_values = [t["count"] for t in by_type[:10]]
            fig_type = go.Figure(data=[go.Bar(
                x=type_values, y=type_labels,
                orientation="h",
                marker_color="#22D3EE",
            )])
            fig_type.update_layout(
                title_text="Eventos por tipo",
                height=300,
                margin={"t": 40, "b": 20, "l": 10, "r": 20},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#F3F4F6"},
                yaxis={"autorange": "reversed"},
                xaxis={"gridcolor": "#374151"},
            )
            st.plotly_chart(fig_type, use_container_width=True)

        # Gráfico 3: Serie temporal (línea)
        time_series = summary_data.get("time_series", [])
        if time_series:
            ts_hours = [t["hour"] for t in time_series]
            ts_counts = [t["count"] for t in time_series]
            fig_ts = go.Figure(data=[go.Scatter(
                x=ts_hours, y=ts_counts,
                mode="lines+markers",
                line={"color": "#22D3EE", "width": 2},
                marker={"size": 6},
                fill="tozeroy",
                fillcolor="rgba(34,211,238,0.1)",
            )])
            fig_ts.update_layout(
                title_text="Eventos por hora",
                height=260,
                margin={"t": 40, "b": 20, "l": 20, "r": 20},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#F3F4F6"},
                xaxis={"gridcolor": "#374151"},
                yaxis={"gridcolor": "#374151"},
            )
            st.plotly_chart(fig_ts, use_container_width=True)

        # Métricas de correlación
        correlated = summary_data.get("correlated_count", 0)
        individual = summary_data.get("individual_count", 0)
        st.markdown(f"**Correlacionados:** {correlated} · **Individuales:** {individual}")

    st.divider()

    # --- EXPORTAR DATOS (Fase 5.9, recomendación #10) ---
    st.subheader("💾 Exportar datos")
    st.caption("Descarga los eventos filtrados de la página actual")
    if "events_list" in st.session_state and st.session_state.events_list:
        export_data = st.session_state.events_list

        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=[
            "id", "received_at", "source_ip", "severity", "event_type",
            "ai_explanation", "analyzed", "correlation_group",
        ])
        writer.writeheader()
        for ev in export_data:
            writer.writerow({
                "id": ev.get("id"),
                "received_at": ev.get("received_at"),
                "source_ip": ev.get("source_ip"),
                "severity": ev.get("severity", ""),
                "event_type": ev.get("event_type", ""),
                "ai_explanation": ev.get("ai_explanation", ""),
                "analyzed": ev.get("analyzed", False),
                "correlation_group": ev.get("correlation_group", ""),
            })
        csv_bytes = csv_buf.getvalue().encode("utf-8")

        json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")

        ecol1, ecol2 = st.columns(2)
        ecol1.download_button(
            "📥 Descargar CSV",
            data=csv_bytes,
            file_name="eventos_ai_noc.csv",
            mime="text/csv",
        )
        ecol2.download_button(
            "📥 Descargar JSON",
            data=json_bytes,
            file_name="eventos_ai_noc.json",
            mime="application/json",
        )
    else:
        st.info("No hay eventos para exportar.")

    st.divider()

    # --- REPORTE ON-DEMAND (Fase 5.9, recomendación #12) ---
    st.subheader("📝 Reporte on-demand")
    st.caption("Genera un resumen de los eventos visibles o recién ingeridos")
    report_source = st.radio(
        "Fuente del reporte",
        ["Eventos filtrados actualmente", "Último lote ingerido"],
        horizontal=True,
    )
    if st.button("Generar reporte", type="primary"):
        with st.spinner("Generando reporte..."):
            try:
                if report_source == "Eventos filtrados actualmente":
                    resp_events = httpx.get(
                        f"{BACKEND_URL}/events",
                        params={"limit": 500},
                        timeout=10,
                        trust_env=False,
                    ).json()
                    report_items = resp_events.get("items", [])
                else:
                    resp_events = httpx.get(
                        f"{BACKEND_URL}/events",
                        params={"limit": 50, "sort_by": "id", "sort_dir": "desc"},
                        timeout=10,
                        trust_env=False,
                    ).json()
                    report_items = resp_events.get("items", [])

                if not report_items:
                    st.info("No hay eventos para generar el reporte.")
                else:
                    total_events = len(report_items)
                    severities = {}
                    types = {}
                    analyzed_count = 0
                    correlated_count = 0
                    for ev in report_items:
                        sev = ev.get("severity") or "sin clasificar"
                        severities[sev] = severities.get(sev, 0) + 1
                        etype = ev.get("event_type") or "sin clasificar"
                        types[etype] = types.get(etype, 0) + 1
                        if ev.get("analyzed"):
                            analyzed_count += 1
                        if ev.get("correlation_group") is not None:
                            correlated_count += 1

                    report_lines = [
                        "## Reporte de eventos — AI-NOC Copilot",
                        "",
                        f"**Total de eventos:** {total_events}",
                        f"**Analizados:** {analyzed_count} / {total_events}",
                        f"**Correlacionados:** {correlated_count}",
                        "",
                        "### Distribución por severidad",
                    ]
                    for sev, count in sorted(severities.items()):
                        report_lines.append(f"- **{sev}:** {count}")
                    report_lines.extend([
                        "",
                        "### Distribución por tipo de evento",
                    ])
                    for etype, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
                        report_lines.append(f"- **{etype}:** {count}")
                    report_lines.extend([
                        "",
                        "---",
                        f"*Generado automáticamente por AI-NOC Copilot — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
                    ])

                    report_text = "\n".join(report_lines)
                    st.markdown(report_text)
                    st.download_button(
                        "📥 Descargar reporte",
                        data=report_text.encode("utf-8"),
                        file_name="reporte_ai_noc.md",
                        mime="text/markdown",
                    )
            except httpx.HTTPError as exc:
                st.error(f"Error al generar reporte: {exc}")

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

    st.divider()
    st.subheader("📜 Histórico de correlación")
    if st.button("Actualizar histórico", key="refresh_history"):
        st.session_state["_reload_history"] = True
        st.rerun()

    try:
        history = httpx.get(
            f"{BACKEND_URL}/events/correlation-history",
            params={"limit": 50},
            timeout=10,
            trust_env=False,
        ).json()
    except httpx.HTTPError:
        history = {"total_groups": 0, "groups": []}

    total_groups = history.get("total_groups", 0)
    groups = history.get("groups", [])

    if total_groups == 0:
        st.info("No hay grupos de correlación en el histórico.")
    else:
        st.caption(f"{total_groups} grupo(s) registrado(s)")
        for g in groups:
            pattern = g.get("pattern")
            icon = PATTERN_ICONS.get(pattern, "❓")
            pattern_label = pattern or "indeterminado"
            ips = ", ".join(g.get("attacker_ips", []))
            sev = g.get("severity", "low")
            badge = _severity_badge(sev)
            first = g.get("first_seen", "")[:16].replace("T", " ")
            last = g.get("last_seen", "")[:16].replace("T", " ")
            event_ids = g.get("event_ids", [])

            header = (
                f"{icon} **Grupo #{g['correlation_group']}** — "
                f"{ips} ({g['event_count']} eventos) · {badge} · {pattern_label}"
            )
            with st.expander(header):
                st.markdown(f"**Patrón:** `{pattern_label}`")
                st.markdown(f"**Severidad:** `{sev}`")
                st.markdown(f"**IP(s) atacante(s):** {ips}")
                st.markdown(f"**Puertos únicos:** {len(g.get('unique_ports', []))}")
                st.markdown(f"**Ventana:** {first} → {last}")
                with st.expander("IDs de eventos", expanded=False):
                    st.caption(", ".join(map(str, event_ids)))

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

    with st.expander("🗓️ Filtros de fecha y ID"):
        dcol1, dcol2 = st.columns(2)
        date_from = dcol1.date_input("Desde", value=None, format="DD/MM/YYYY")
        time_from = dcol1.time_input("Hora desde", value=None)
        date_to = dcol2.date_input("Hasta", value=None, format="DD/MM/YYYY")
        time_to = dcol2.time_input("Hora hasta", value=None)

        icol1, icol2 = st.columns(2)
        id_from_raw = icol1.text_input("ID desde", placeholder="ej: 10")
        id_to_raw = icol2.text_input("ID hasta", placeholder="ej: 50")

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

        st.session_state["total_cargado"] = total
        # Guardar eventos para exportar
        st.session_state["events_list"] = events

    except httpx.HTTPError:
        events = []
        total = 0
        st.session_state["total_cargado"] = 0
        st.session_state["events_list"] = []
        st.error("Backend no disponible. ¿Corriste el backend?")

    if not events:
        st.info("No hay eventos que coincidan con los filtros.")

    for event in events:
        received_dt = event["received_at"]
        if isinstance(received_dt, str):
            from datetime import datetime

            received_dt = datetime.fromisoformat(received_dt.replace("Z", "+00:00"))
        timestamp_fmt = received_dt.strftime("%d/%m %H:%M")

        sev = event.get("severity", "")
        analyzed = event.get("analyzed", False)

        status_emoji = _severity_badge(sev, analyzed)

        event_type = event.get("event_type") or "sin analizar"
        source_ip = event["source_ip"]

        label = f"[#{event['id']}] [{timestamp_fmt}] {source_ip} — {event_type} {status_emoji}"

        with st.expander(label):
            st.code(event["raw_message"], language="text")
            if event.get("analyzed"):
                st.markdown(f"**Severidad:** `{event['severity']}`")
                st.markdown(f"**Explicación IA:** {event['ai_explanation']}")

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
                                timeout=30,
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

    # ── Chat interactivo con el copiloto (Fase 5.10) ───────────────────────
    st.divider()

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    chat_toggle_col, chat_help_col = st.columns([5, 1])
    with chat_toggle_col:
        if st.checkbox("💬  Chat con el Copiloto", value=st.session_state.chat_open, key="chat_toggle"):
            st.session_state.chat_open = True
        else:
            st.session_state.chat_open = False
    with chat_help_col:
        st.markdown(
            '<span class="ainoc-chat-help">?'
            '<span class="ainoc-chat-tooltip">'
            'Seleccioná un evento o grupo, escribí tu pregunta y recibí '
            'una explicación detallada. Podés pegar logs adicionales con '
            'el botón 📎 para dar más contexto.'
            '</span></span>',
            unsafe_allow_html=True,
        )

    if st.session_state.chat_open:
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # Selector de destino del chat
        chat_dest = st.radio(
            "Consultar sobre",
            ["Evento individual", "Grupo de correlación"],
            horizontal=True,
            key="chat_dest",
        )

        # Cargar opciones
        chat_options = {}
        if chat_dest == "Evento individual":
            try:
                resp_ev = httpx.get(
                    f"{BACKEND_URL}/events",
                    params={"limit": 100, "sort_by": "id", "sort_dir": "desc"},
                    timeout=5,
                    trust_env=False,
                )
                for ev in resp_ev.json().get("items", []):
                    ts = ev["received_at"][:16].replace("T", " ") if ev.get("received_at") else "?"
                    sev = SEVERITY_COLORS.get(ev.get("severity", ""), "⚪")
                    etype = ev.get("event_type") or "sin analizar"
                    chat_options[f"#{ev['id']} — {ts} — {sev} {etype}"] = ev["id"]
            except httpx.HTTPError:
                st.info("No se pudieron cargar los eventos.")
        else:
            try:
                resp_gr = httpx.get(
                    f"{BACKEND_URL}/events/correlation-history",
                    params={"limit": 50},
                    timeout=5,
                    trust_env=False,
                )
                for g in resp_gr.json().get("groups", []):
                    pat = PATTERN_ICONS.get(g.get("pattern"), "❓")
                    ips = ", ".join(g.get("attacker_ips", []))
                    chat_options[f"Grupo #{g['correlation_group']} — {pat} {ips} ({g['event_count']} evt.)"] = g[
                        "correlation_group"
                    ]
            except httpx.HTTPError:
                st.info("No hay grupos de correlación disponibles.")

        if chat_options:
            selected_label = st.selectbox("Destino", list(chat_options.keys()), key="chat_target")
            selected_id = chat_options[selected_label]
        else:
            st.info("No hay datos disponibles para chatear.")
            selected_id = None

        # Preguntas sugeridas
        if selected_id is not None:
            st.markdown(
                '<div class="ainoc-chips">',
                unsafe_allow_html=True,
            )
            chip_cols = st.columns(4)
            chip_questions = [
                "🔍 ¿Qué significa este evento?",
                "⚠️ ¿Es una amenaza real?",
                "🛡️ ¿Qué debo hacer ahora?",
                "📊 ¿Por qué se clasificó así?",
            ]
            for i, q in enumerate(chip_questions):
                with chip_cols[i]:
                    if st.button(q, key=f"chip_{i}", use_container_width=True):
                        st.session_state["chat_pending_msg"] = q
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Mostrar historial del chat
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(f'<div class="ainoc-msg-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                with st.chat_message("assistant"):
                    st.markdown(f'<div class="ainoc-msg-ai">{msg["content"]}</div>', unsafe_allow_html=True)

        # Input del chat (st.chat_input siempre al fondo)
        if prompt := st.chat_input("Preguntale al copiloto..."):
            st.session_state["chat_pending_msg"] = prompt
            st.rerun()

        # Procesar mensajes pendientes (de chips o del input)
        pending = st.session_state.pop("chat_pending_msg", None)
        if pending and selected_id is not None:
            # Attach de logs
            with st.expander("📎 Adjuntar logs adicionales (opcional)", expanded=False):
                attach = st.text_area(
                    "Pegar líneas de log para agregar contexto",
                    height=80,
                    placeholder="Aug 19 12:00:00 pfsense-prod filterlog: ...",
                    key="chat_attach",
                )

            user_message = pending
            if attach and attach.strip():
                user_message += "\n\n---\n**Logs adicionales adjuntados:**\n```\n" + attach.strip() + "\n```"

            st.session_state.chat_messages.append({"role": "user", "content": user_message})

            with st.chat_message("user"):
                st.markdown(f'<div class="ainoc-msg-user">{user_message}</div>', unsafe_allow_html=True)

            with st.chat_message("assistant"), st.spinner("Consultando al modelo..."):
                # Armar contexto del sistema
                system_parts = [
                    (
                        "Eres un analista de seguridad de redes (copiloto NOC local). "
                        "Tu rol es enseñar y aconsejar al administrador. "
                        "Responde en español, de forma técnica pero clara. "
                        "NUNCA inventes IPs, puertos, ni contexto de red que no esté en los datos reales."
                    ),
                ]

                try:
                    if chat_dest == "Evento individual":
                        ev_data = httpx.get(
                            f"{BACKEND_URL}/events/{selected_id}",
                            timeout=5,
                            trust_env=False,
                        ).json()
                        system_parts.append(f"Evento de log crudo:\n{ev_data.get('raw_message', '')}")
                        if ev_data.get("analyzed"):
                            system_parts.append(
                                f"Análisis previo: severidad={ev_data.get('severity')}, "
                                f"tipo={ev_data.get('event_type')}.\n"
                                f"Explicación: {ev_data.get('ai_explanation', '')}"
                            )
                        if ev_data.get("correlation_group") is not None:
                            gr_data = httpx.get(
                                f"{BACKEND_URL}/events/correlation-history",
                                params={"limit": 50},
                                timeout=5,
                                trust_env=False,
                            ).json()
                            for g in gr_data.get("groups", []):
                                if g["correlation_group"] == ev_data["correlation_group"]:
                                    system_parts.append(
                                        f"Grupo de correlación #{g['correlation_group']}: "
                                        f"{g['event_count']} eventos, patrón={g.get('pattern', 'indeterminado')}."
                                    )
                                    break
                    else:
                        gr_data = httpx.get(
                            f"{BACKEND_URL}/events/correlation-history",
                            params={"limit": 50},
                            timeout=5,
                            trust_env=False,
                        ).json()
                        for g in gr_data.get("groups", []):
                            if g["correlation_group"] == selected_id:
                                system_parts.append(
                                    f"Grupo de correlación #{selected_id}:\n"
                                    f"IP(s) atacante(s): {', '.join(g.get('attacker_ips', []))}\n"
                                    f"Patrón: {g.get('pattern', 'indeterminado')}\n"
                                    f"Cantidad de eventos: {g['event_count']}\n"
                                    f"Severidad: {g.get('severity', 'low')}"
                                )
                                break
                except httpx.HTTPError:
                    system_parts.append("(No se pudo cargar el contexto detallado del destino)")

                system_message = "\n\n".join(system_parts)
                messages = [{"role": "system", "content": system_message}] + st.session_state.chat_messages

                # Streaming de la respuesta
                import time as _time

                t0 = _time.perf_counter()

                def _chat_stream():
                    with httpx.stream(
                        "POST",
                        f"{BACKEND_URL}/events/{selected_id}/chat",
                        json={"message": user_message, "history": st.session_state.chat_messages[:-1]},
                        timeout=120,
                        trust_env=False,
                    ) as resp:
                        for chunk in resp.iter_text():
                            if chunk:
                                yield chunk

                response = st.write_stream(_chat_stream())
                elapsed = _time.perf_counter() - t0

                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                st.caption(f"⏱️ {elapsed:.1f}s")
