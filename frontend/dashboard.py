import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI-NOC Copilot", layout="wide")
st.title("🛰️ AI-NOC Copilot")
st.caption("Prototipo local — pfSense syslog + Ollama, 100% offline")

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
    try:
        events = httpx.get(
            f"{BACKEND_URL}/events",
            params={"only_unanalyzed": only_new},
            timeout=5,
            trust_env=False,
        ).json()
    except httpx.HTTPError:
        events = []
        st.error("Backend no disponible. ¿Corriste el backend?")

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