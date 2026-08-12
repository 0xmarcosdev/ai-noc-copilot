import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI-NOC Copilot", layout="wide")
st.title("🛰️ AI-NOC Copilot")
st.caption("Prototipo local — pfSense syslog + Ollama, 100% offline")

col1, col2 = st.columns([2, 1])

with col2:
    st.subheader("Resumen")
    try:
        summary = httpx.get(f"{BACKEND_URL}/summary", timeout=5).json()
        st.metric("Eventos analizados", summary["total_analyzed"])
        for sev, count in summary.get("by_severity", {}).items():
            st.write(f"**{sev}**: {count}")
    except httpx.HTTPError:
        st.warning("No se pudo conectar al backend.")

with col1:
    st.subheader("Eventos recientes")
    only_new = st.checkbox("Solo sin analizar", value=False)
    try:
        events = httpx.get(
            f"{BACKEND_URL}/events",
            params={"only_unanalyzed": only_new},
            timeout=5,
        ).json()
    except httpx.HTTPError:
        events = []
        st.error("Backend no disponible. ¿Corriste `docker compose up`?")

    for event in events:
        with st.expander(f"[{event['received_at']}] {event['source_ip']} — {event.get('event_type') or 'sin analizar'}"):
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
                        )
                    if resp.status_code == 200:
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.text}")
