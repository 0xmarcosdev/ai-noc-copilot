import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI-NOC Copilot", layout="wide")
st.title("🛰️ AI-NOC Copilot")
st.caption("Prototipo local — pfSense syslog + Ollama, 100% offline")

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
                st.success(f"{data['ingested']} eventos ingeridos")
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(f"Error al ingerir: {exc}")
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
        "Severidad", ["", "low", "medium", "high"],
        format_func=lambda s: "Todas" if s == "" else s,
    )
    type_filter = fcol2.text_input("Tipo de evento (parcial)")

    page_size = st.selectbox("Por página", [10, 25, 50], index=1)
    filter_state = (only_new, search_q, sev_filter, type_filter, page_size)
    if st.session_state.get("events_filters") != filter_state:
        st.session_state["events_page"] = 0
        st.session_state["events_filters"] = filter_state
    page = st.session_state.get("events_page", 0)

    try:
        payload = httpx.get(
            f"{BACKEND_URL}/events",
            params={
                "only_unanalyzed": only_new,
                "q": search_q or None,
                "severity": sev_filter or None,
                "event_type": type_filter or None,
                "limit": page_size,
                "offset": page * page_size,
            },
            timeout=5,
            trust_env=False,
        ).json()
        events = payload.get("items", [])
        total = payload.get("total", 0)
    except httpx.HTTPError:
        events = []
        total = 0
        st.error("Backend no disponible. ¿Corriste el backend?")

    if not events:
        st.info("No hay eventos que coincidan con los filtros.")
    for event in events:
        label = f"[{event['received_at']}] {event['source_ip']} — {event.get('event_type') or 'sin analizar'}"
        with st.expander(label):
            st.code(event["raw_message"], language="text")
            if event.get("analyzed"):
                st.markdown(f"**Severidad:** `{event['severity']}`")
                st.markdown(f"**Explicación IA:** {event['ai_explanation']}")
            else:
                if st.button("Explicar con IA", key=f"analyze-{event['id']}"):
                    with st.spinner("Consultando al modelo local..."):
                        resp = httpx.post(
                            f"{BACKEND_URL}/events/{event['id']}/analyze",
                            timeout=90,
                            trust_env=False,
                        )
                    if resp.status_code == 200:
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")

    prev_disabled = page == 0
    next_disabled = (page + 1) * page_size >= total
    pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
    if pcol1.button("← Anterior", disabled=prev_disabled):
        st.session_state["events_page"] = page - 1
        st.rerun()
    pcol2.markdown(f"Página {page + 1} — {total} eventos")
    if pcol3.button("Siguiente →", disabled=next_disabled):
        st.session_state["events_page"] = page + 1
        st.rerun()
