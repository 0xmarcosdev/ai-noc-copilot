import csv
import html
import io
import json
import os
import re
from datetime import datetime, time

import httpx
import streamlit as st

st.set_page_config(
    page_title="AI-NOC Copilot",
    layout="wide",
    page_icon="static/favicon.svg",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

SORT_FIELDS = {
    "Fecha de recepción": "received_at",
    "ID": "id",
    "Severidad": "severity",
    "Tipo de evento": "event_type",
}
SORT_LABELS = list(SORT_FIELDS.keys())

SEVERITY_COLORS = {"high": "🔴", "medium": "🟠", "low": "🟢"}
SEVERITY_HEX = {"high": "#E11D48", "medium": "#D97706", "low": "#059669"}
PATTERN_ICONS = {"fuerza_bruta": "🎯", "escaneo_puertos": "📡"}


def _parse_id(texto: str) -> int | None:
    texto = (texto or "").strip()
    return int(texto) if texto.isdigit() else None


def _severity_title_badge(severity: str | None, analyzed: bool = True) -> str:
    sev = severity or "low"
    icon = SEVERITY_COLORS.get(sev, "⚪")
    check = "✓" if analyzed else ""
    return f"{icon} {sev.upper()} {check}".strip()


def _severity_content_badge(severity: str | None, analyzed: bool = True) -> str:
    sev = severity or "low"
    icon = SEVERITY_COLORS.get(sev, "⚪")
    badge_class = f"ainoc-badge-{sev}"
    check = " ✓" if analyzed else ""
    return f'<span class="{badge_class}">{icon} {sev.upper()}{check}</span>'


def _event_header(event: dict) -> str:
    received_dt = event["received_at"]
    if isinstance(received_dt, str):
        received_dt = datetime.fromisoformat(received_dt.replace("Z", "+00:00"))
    ts = received_dt.strftime("%d/%m %H:%M")
    sev = event.get("severity") or ""
    analyzed = event.get("analyzed", False)
    badge = _severity_title_badge(sev, analyzed) if sev or analyzed else "⚪ SIN ANALIZAR"
    etype = event.get("event_type") or "sin analizar"
    if len(etype) > 40:
        etype = etype[:37] + "…"
    ip = event.get("source_ip") or "?"
    corr = event.get("correlation_group")
    gtag = f"  ·  G#{corr}" if corr is not None else ""
    return f"{badge}   #{event['id']}  ·  {ts}  ·  {ip}  ·  {etype}{gtag}"


def _md_lite_to_html(text: str) -> str:
    """Convierte markdown simple a HTML con clases uniformes (sin discrepancias de fuente)."""
    if not text:
        return ""
    # Escapar primero, luego reintroducir marcas controladas
    t = html.escape(text)
    # code blocks ```
    t = re.sub(
        r"```([\s\S]*?)```",
        r'<pre class="ainoc-code">\1</pre>',
        t,
    )
    # inline code
    t = re.sub(r"`([^`]+)`", r'<code class="ainoc-code-inline">\1</code>', t)
    # bold ** **
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    # headers ### ## #
    t = re.sub(r"^### (.+)$", r'<div class="ainoc-h">\1</div>', t, flags=re.MULTILINE)
    t = re.sub(r"^## (.+)$", r'<div class="ainoc-h">\1</div>', t, flags=re.MULTILINE)
    t = re.sub(r"^# (.+)$", r'<div class="ainoc-h">\1</div>', t, flags=re.MULTILINE)
    # list items
    t = re.sub(r"^- (.+)$", r'<div class="ainoc-li">• \1</div>', t, flags=re.MULTILINE)
    t = re.sub(r"^\* (.+)$", r'<div class="ainoc-li">• \1</div>', t, flags=re.MULTILINE)
    # paragraphs: double newlines
    parts = re.split(r"\n\n+", t)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<div") or p.startswith("<pre"):
            out.append(p.replace("\n", "<br>"))
        else:
            out.append(f'<p class="ainoc-p">{p.replace(chr(10), "<br>")}</p>')
    return "".join(out)


def _render_chat_html(messages: list[dict]) -> str:
    """Todo el historial como un único bloque HTML scrolleable."""
    if not messages:
        return (
            '<div class="ainoc-chat-empty">'
            "Los mensajes aparecen aquí. Escribí abajo o usá una pregunta sugerida."
            "</div>"
        )
    chunks = []
    for msg in messages:
        if msg["role"] == "user":
            display = msg["content"].split("\n\n---\n**CONTEXTO")[0]
            chunks.append(f'<div class="ainoc-msg-user">{html.escape(display)}</div>')
        else:
            body = _md_lite_to_html(msg["content"])
            chunks.append(f'<div class="ainoc-msg-ai">{body}</div>')
    return "".join(chunks)


# ── Tema (no tocar chat_messages al cambiar) ────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

DARK_VARS = """
    --ainoc-bg: #0B1220;
    --ainoc-panel: #111827;
    --ainoc-elevated: #1E293B;
    --ainoc-border: #334155;
    --ainoc-accent: #0891B2;
    --ainoc-accent-dim: #0E7490;
    --ainoc-accent-hover: #155E75;
    --ainoc-text: #F1F5F9;
    --ainoc-muted: #94A3B8;
    --ainoc-placeholder: #64748B;
    --ainoc-danger: #FB7185;
    --ainoc-warning: #FBBF24;
    --ainoc-success: #34D399;
    --ainoc-chat-user-bg: linear-gradient(135deg, #0891B2 0%, #0E7490 100%);
    --ainoc-chat-user-text: #FFFFFF;
    --ainoc-chat-ai-bg: #1E293B;
    --ainoc-chat-ai-border: #334155;
    --ainoc-input-bg: #1E293B;
    --ainoc-shadow: rgba(0,0,0,0.4);
    --ainoc-chart-text: #CBD5E1;
    --ainoc-dropzone-bg: #1E293B;
    --ainoc-dropzone-border: #475569;
    --ainoc-code-bg: #0F172A;
    --ainoc-code-text: #E2E8F0;
"""

LIGHT_VARS = """
    --ainoc-bg: #F8FAFC;
    --ainoc-panel: #FFFFFF;
    --ainoc-elevated: #F1F5F9;
    --ainoc-border: #CBD5E1;
    --ainoc-accent: #0E7490;
    --ainoc-accent-dim: #155E75;
    --ainoc-accent-hover: #164E63;
    --ainoc-text: #0F172A;
    --ainoc-muted: #334155;
    --ainoc-placeholder: #64748B;
    --ainoc-danger: #E11D48;
    --ainoc-warning: #B45309;
    --ainoc-success: #047857;
    --ainoc-chat-user-bg: linear-gradient(135deg, #0E7490 0%, #155E75 100%);
    --ainoc-chat-user-text: #FFFFFF;
    --ainoc-chat-ai-bg: #F1F5F9;
    --ainoc-chat-ai-border: #CBD5E1;
    --ainoc-input-bg: #FFFFFF;
    --ainoc-shadow: rgba(15, 23, 42, 0.1);
    --ainoc-chart-text: #1E293B;
    --ainoc-dropzone-bg: #F1F5F9;
    --ainoc-dropzone-border: #94A3B8;
    --ainoc-code-bg: #F1F5F9;
    --ainoc-code-text: #0F172A;
"""

is_dark = st.session_state.theme == "dark"
theme_vars = DARK_VARS if is_dark else LIGHT_VARS
PLOTLY_FONT = "#CBD5E1" if is_dark else "#1E293B"
PLOTLY_GRID = "#334155" if is_dark else "#CBD5E1"
PLOTLY_PAPER = "rgba(0,0,0,0)"

BRANDING_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

    :root {{
        {theme_vars}
    }}

    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 0 !important;
        min-height: 0 !important;
    }}
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    .stDeployButton {{ display: none !important; }}
    #MainMenu, footer {{ visibility: hidden !important; }}

    html, body, .stApp {{
        font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
        background-color: var(--ainoc-bg) !important;
        color: var(--ainoc-text) !important;
    }}
    .stApp {{ background-color: var(--ainoc-bg) !important; }}
    .block-container {{
        padding-top: 0.75rem !important;
        padding-bottom: 1rem !important;
        max-width: 1360px !important;
    }}

    h1, h2, h3, h4 {{
        font-family: 'JetBrains Mono', monospace !important;
        color: var(--ainoc-text) !important;
        font-weight: 700 !important;
    }}
    h3 {{ font-size: 1rem !important; margin: 0.15rem 0 0.4rem 0 !important; }}

    p, .stMarkdown, .stCaption {{
        font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
        color: var(--ainoc-text) !important;
    }}
    label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] {{
        color: var(--ainoc-muted) !important;
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }}
    /* Código / logs: fondo y texto del tema (legible en claro y oscuro) */
    code, pre, .stCode, [data-testid="stCode"],
    [data-testid="stCode"] pre, [data-testid="stCode"] code {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.78rem !important;
        color: var(--ainoc-code-text) !important;
        background-color: var(--ainoc-code-bg) !important;
    }}
    [data-testid="stCode"] {{
        background-color: var(--ainoc-code-bg) !important;
        border: 1px solid var(--ainoc-border) !important;
        border-radius: 6px !important;
    }}

    /* Placeholders visibles en ambos temas */
    input::placeholder, textarea::placeholder,
    .stTextInput input::placeholder, .stNumberInput input::placeholder {{
        color: var(--ainoc-placeholder) !important;
        opacity: 1 !important;
    }}

    /* Markdown / tipos dominantes / listas */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    .stMarkdown code, .stCaption {{
        color: var(--ainoc-text) !important;
    }}
    .stMarkdown code {{
        background-color: var(--ainoc-elevated) !important;
        color: var(--ainoc-text) !important;
        padding: 1px 5px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
    }}

    /* Popover (botón IDs del histórico) legible en claro */
    [data-testid="stPopover"] button,
    div[data-testid="stPopover"] > button {{
        background-color: var(--ainoc-elevated) !important;
        color: var(--ainoc-text) !important;
        border: 1px solid var(--ainoc-border) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
    }}
    [data-testid="stPopover"] button:hover {{
        border-color: var(--ainoc-accent) !important;
        color: var(--ainoc-accent) !important;
    }}

    button[data-baseweb="tab"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 0.8rem !important;
        color: var(--ainoc-muted) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: var(--ainoc-accent) !important;
    }}

    details[data-testid="stExpander"] {{
        background-color: var(--ainoc-panel) !important;
        border: 1px solid var(--ainoc-border) !important;
        border-radius: 8px !important;
        margin-bottom: 5px !important;
    }}
    details[data-testid="stExpander"] > summary,
    details[data-testid="stExpander"] > summary * {{
        color: var(--ainoc-text) !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        font-family: 'JetBrains Mono', monospace !important;
    }}
    details[data-testid="stExpander"] .stMarkdown,
    details[data-testid="stExpander"] p,
    details[data-testid="stExpander"] span,
    details[data-testid="stExpander"] li {{
        color: var(--ainoc-text) !important;
    }}
    details[data-testid="stExpander"] [data-testid="stCode"],
    details[data-testid="stExpander"] pre,
    details[data-testid="stExpander"] code {{
        background-color: var(--ainoc-code-bg) !important;
        color: var(--ainoc-code-text) !important;
    }}

    button[data-testid="baseButton-primary"],
    div[data-testid="stButton"] > button[kind="primary"] {{
        background-color: var(--ainoc-accent) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.76rem !important;
        border: none !important;
        border-radius: 7px !important;
        box-shadow: 0 2px 6px rgba(8, 145, 178, 0.28) !important;
    }}
    button[data-testid="baseButton-primary"]:hover,
    div[data-testid="stButton"] > button[kind="primary"]:hover {{
        background-color: var(--ainoc-accent-hover) !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stButton"] > button:not([kind="primary"]) {{
        background-color: var(--ainoc-elevated) !important;
        color: var(--ainoc-text) !important;
        border: 1px solid var(--ainoc-border) !important;
        border-radius: 7px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 0.74rem !important;
    }}
    div[data-testid="stDownloadButton"] > button {{
        background-color: var(--ainoc-accent) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
        border: none !important;
        border-radius: 7px !important;
    }}

    input, textarea, .stTextInput input, .stNumberInput input {{
        background-color: var(--ainoc-input-bg) !important;
        color: var(--ainoc-text) !important;
        border: 1px solid var(--ainoc-border) !important;
        border-radius: 7px !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }}
    input:focus, textarea:focus {{
        border-color: var(--ainoc-accent) !important;
        box-shadow: 0 0 0 2px rgba(8, 145, 178, 0.2) !important;
    }}

    /* Radios: opciones fijas, no editables */
    [data-testid="stRadio"] label span,
    [data-testid="stCheckbox"] label span {{
        color: var(--ainoc-text) !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 500 !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        font-size: 0.84rem !important;
    }}

    div[data-testid="stMetric"] {{
        background-color: var(--ainoc-panel) !important;
        padding: 8px 10px !important;
        border-radius: 8px !important;
        border: 1px solid var(--ainoc-border) !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: var(--ainoc-text) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
    }}

    .ainoc-badge-high {{
        display: inline-block; background: rgba(225,29,72,0.14); color: var(--ainoc-danger);
        padding: 2px 8px; border-radius: 5px; font-weight: 800; font-size: 0.66rem;
        font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
        border: 1px solid rgba(225,29,72,0.35);
    }}
    .ainoc-badge-medium {{
        display: inline-block; background: rgba(180,83,9,0.14); color: var(--ainoc-warning);
        padding: 2px 8px; border-radius: 5px; font-weight: 800; font-size: 0.66rem;
        font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
        border: 1px solid rgba(180,83,9,0.35);
    }}
    .ainoc-badge-low {{
        display: inline-block; background: rgba(4,120,87,0.14); color: var(--ainoc-success);
        padding: 2px 8px; border-radius: 5px; font-weight: 800; font-size: 0.66rem;
        font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
        border: 1px solid rgba(4,120,87,0.35);
    }}

    [data-testid="stFileUploader"] section {{
        background-color: var(--ainoc-dropzone-bg) !important;
        border: 1px dashed var(--ainoc-dropzone-border) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stFileUploader"] section * {{
        color: var(--ainoc-muted) !important;
    }}

    /* ── Chat frame: un solo bloque HTML con scroll real ── */
    .ainoc-chat-frame {{
        border: 1px solid var(--ainoc-border);
        border-radius: 12px;
        background: var(--ainoc-panel);
        box-shadow: 0 4px 16px var(--ainoc-shadow);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        height: 480px;
        max-height: 55vh;
        margin-bottom: 0.5rem;
    }}
    .ainoc-chat-top {{
        padding: 10px 14px;
        background: var(--ainoc-elevated);
        border-bottom: 1px solid var(--ainoc-border);
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 0.8rem;
        color: var(--ainoc-text);
        flex: 0 0 auto;
    }}
    .ainoc-chat-scroll {{
        flex: 1 1 auto;
        overflow-y: auto;
        padding: 14px;
        background: var(--ainoc-bg);
        min-height: 0;
    }}
    .ainoc-chat-empty {{
        color: var(--ainoc-muted);
        font-size: 0.85rem;
        text-align: center;
        padding: 3rem 1rem;
        font-family: 'IBM Plex Sans', sans-serif;
    }}
    .ainoc-msg-user {{
        background: var(--ainoc-chat-user-bg);
        color: var(--ainoc-chat-user-text);
        padding: 10px 14px;
        border-radius: 14px 14px 4px 14px;
        max-width: 78%;
        margin: 8px 0 8px auto;
        font-size: 0.875rem;
        line-height: 1.5;
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(8,145,178,0.2);
        word-wrap: break-word;
        white-space: pre-wrap;
    }}
    /* Respuestas IA: tipografía UNIFORME en todos los hijos */
    .ainoc-msg-ai {{
        background: var(--ainoc-chat-ai-bg);
        color: var(--ainoc-text);
        padding: 12px 14px;
        border-radius: 14px 14px 14px 4px;
        max-width: 85%;
        margin: 8px 0;
        border: 1px solid var(--ainoc-chat-ai-border);
        font-size: 0.875rem;
        line-height: 1.55;
        font-family: 'IBM Plex Sans', sans-serif;
        font-weight: 400;
        box-shadow: 0 1px 3px var(--ainoc-shadow);
        word-wrap: break-word;
    }}
    .ainoc-msg-ai .ainoc-p,
    .ainoc-msg-ai .ainoc-li,
    .ainoc-msg-ai .ainoc-h,
    .ainoc-msg-ai p,
    .ainoc-msg-ai div,
    .ainoc-msg-ai span,
    .ainoc-msg-ai li {{
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
        color: var(--ainoc-text) !important;
        line-height: 1.55 !important;
        margin: 0.35em 0 !important;
    }}
    .ainoc-msg-ai .ainoc-h,
    .ainoc-msg-ai strong {{
        font-weight: 700 !important;
        color: var(--ainoc-accent) !important;
        font-size: 0.875rem !important;
    }}
    .ainoc-msg-ai .ainoc-code,
    .ainoc-msg-ai .ainoc-code-inline,
    .ainoc-msg-ai code,
    .ainoc-msg-ai pre {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        background: var(--ainoc-elevated) !important;
        color: var(--ainoc-text) !important;
        border-radius: 4px;
        padding: 2px 5px;
    }}
    .ainoc-msg-ai .ainoc-code,
    .ainoc-msg-ai pre {{
        display: block;
        padding: 8px 10px;
        overflow-x: auto;
        margin: 0.5em 0;
    }}

    .ainoc-context-card {{
        background: var(--ainoc-elevated);
        border: 1px solid var(--ainoc-border);
        border-left: 3px solid var(--ainoc-accent);
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.75rem;
        line-height: 1.4;
        margin: 0.4rem 0 0.6rem 0;
        color: var(--ainoc-muted);
        font-family: 'JetBrains Mono', monospace;
    }}
    .ainoc-context-card strong {{ color: var(--ainoc-text); font-weight: 700; }}

    .ainoc-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.28rem;
        font-weight: 800;
        color: var(--ainoc-text);
        line-height: 1.2;
    }}
    .ainoc-tagline {{
        color: var(--ainoc-muted);
        font-size: 0.78rem;
        font-weight: 500;
    }}

    /* Panel de filtros: tarjetas alineadas */
    .ainoc-filter-panel {{
        background: var(--ainoc-panel);
        border: 1px solid var(--ainoc-border);
        border-radius: 10px;
        padding: 12px 14px 8px 14px;
        margin-bottom: 0.6rem;
    }}

    hr {{ border-color: var(--ainoc-border) !important; margin: 0.5rem 0 !important; }}
    div[data-testid="stVerticalBlock"] > div {{ gap: 0.3rem !important; }}

    ::-webkit-scrollbar {{ width: 7px; height: 7px; }}
    ::-webkit-scrollbar-track {{ background: var(--ainoc-bg); }}
    ::-webkit-scrollbar-thumb {{ background: var(--ainoc-border); border-radius: 4px; }}

    [data-testid="stChatInput"] textarea {{
        background-color: var(--ainoc-input-bg) !important;
        color: var(--ainoc-text) !important;
        border: 1px solid var(--ainoc-border) !important;
    }}
</style>
"""

st.markdown(BRANDING_CSS, unsafe_allow_html=True)

AINOC_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="34" height="34" role="img" aria-label="AI-NOC">
  <defs><style>
    .ring{fill:none;stroke:#0891B2;stroke-width:2.25;stroke-linecap:round}
    .ring-dim{fill:none;stroke:#0891B2;stroke-width:1.25;opacity:.35}
    .node,.blip{fill:#0891B2}
    .sweep-line{fill:none;stroke:#0891B2;stroke-width:1.75;stroke-linecap:round;opacity:.9}
    .sweep-wedge{fill:#0891B2;opacity:.14}
    .sweep-group{transform-origin:0px 0px;animation:ainoc-sweep 3s linear infinite}
    .blip{animation:ainoc-pulse 2.4s ease-in-out infinite}
    .blip-b{animation-delay:.8s}.blip-c{animation-delay:1.6s}
    @keyframes ainoc-sweep{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    @keyframes ainoc-pulse{0%,100%{opacity:1}50%{opacity:.35}}
    @media (prefers-reduced-motion:reduce){.sweep-group,.blip{animation:none!important}}
  </style></defs>
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

# Header
hc1, hc2 = st.columns([5.5, 1.15])
with hc1:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;">
          <div style="width:34px;height:34px;">{AINOC_LOGO_SVG}</div>
          <div>
            <div class="ainoc-title">AI-NOC Copilot</div>
            <div class="ainoc-tagline">Copiloto local de logs de pfSense — 100 % offline</div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )
with hc2:
    theme_label = "☀️ Claro" if is_dark else "🌙 Oscuro"
    if st.button(theme_label, key="theme_toggle", use_container_width=True):
        # Solo cambia tema; chat_messages y demás session_state se preservan
        st.session_state.theme = "light" if is_dark else "dark"
        st.rerun()

if "notification" in st.session_state:
    n = st.session_state.notification
    if n["type"] == "success":
        st.success(n["message"], icon="✅")
    elif n["type"] == "error":
        st.error(n["message"], icon="❌")
    elif n["type"] == "info":
        st.info(n["message"], icon="ℹ️")
    del st.session_state.notification

if "refrescar_total_anterior" not in st.session_state:
    st.session_state.refrescar_total_anterior = None

if st.button("↻ Actualizar", key="refresh_btn"):
    st.session_state.refrescar_total_anterior = st.session_state.get("total_cargado", 0)
    st.rerun()

if st.session_state.get("refrescar_total_anterior") is not None:
    ant = st.session_state.refrescar_total_anterior
    nuevo = st.session_state.get("total_cargado", 0)
    if nuevo != ant:
        d = nuevo - ant
        msg = f"📊 {d} eventos nuevos" if d > 0 else f"📉 {abs(d)} eventos eliminados"
        st.session_state.notification = {"type": "info", "message": msg}
        st.rerun()
    st.session_state.refrescar_total_anterior = None

with st.expander("📥 Ingesta manual de logs", expanded=False):
    pasted = st.text_area(
        "Pegar logs (una línea por evento)",
        height=100,
        placeholder="Aug 19 12:00:00 pfsense-prod filterlog: ...",
        key="ingest_paste",
    )
    uploaded = st.file_uploader(
        "Subir archivo (.log / .txt)",
        type=["log", "txt"],
        key="ingest_file",
    )
    if st.button("Ingerir logs", type="primary", key="ingest_btn"):
        content = None
        if uploaded is not None:
            content = uploaded.getvalue().decode("utf-8", errors="replace")
        elif pasted and pasted.strip():
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
                st.session_state.notification = {"type": "error", "message": f"❌ Error: {exc}"}
                st.rerun()
        else:
            st.warning("Pegá logs o subí un archivo primero.")
    st.caption("Sanitizá IPs internas antes de pegar logs reales (SPEC §8).")

tab_events, tab_chat, tab_corr, tab_perf, tab_about = st.tabs(["📋 Eventos", "💬 Chat", "🔗 Correlación", "⚡ Rendimiento", "ℹ️ Acerca del proyecto"])

# ── TAB EVENTOS ─────────────────────────────────────────────────────────────
with tab_events:
    main_col, side_col = st.columns([2.2, 1], gap="medium")

    with side_col:
        st.markdown("### Resumen")
        summary_data = None
        try:
            summary_data = httpx.get(f"{BACKEND_URL}/summary", timeout=5, trust_env=False).json()
            m1, m2 = st.columns(2)
            m1.metric("Analizados", summary_data.get("total_analyzed", 0))
            by_sev = summary_data.get("by_severity", {})
            m2.metric("High", by_sev.get("high", 0))
            st.caption(f"medium: {by_sev.get('medium', 0)} · low: {by_sev.get('low', 0)}")
        except httpx.HTTPError:
            st.warning("No se pudo conectar al backend.")

        top_types = (summary_data or {}).get("top_high_severity_types", [])
        if top_types:
            st.markdown("**Tipos dominantes (high)**")
            for item in top_types[:4]:
                st.markdown(f"- `{item['event_type']}` · **{item['count']}**")

        if summary_data:
            import plotly.graph_objects as go

            by_sev = summary_data.get("by_severity", {})
            if by_sev:
                labels = list(by_sev.keys())
                values = list(by_sev.values())
                colors = [SEVERITY_HEX.get(s, "#64748B") for s in labels]
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            marker={
                                "colors": colors,
                                "line": {"color": "#0B1220" if is_dark else "#FFFFFF", "width": 2},
                            },
                            hole=0.42,
                            textinfo="label+value",
                            textfont={"size": 13, "family": "JetBrains Mono", "color": PLOTLY_FONT},
                            hovertemplate="<b>%{label}</b><br>Eventos: %{value}<br>%{percent}<extra></extra>",
                            pull=[0.05 if v == max(values) else 0 for v in values],
                        )
                    ]
                )
                fig.update_layout(
                    title={
                        "text": "Severidad",
                        "font": {"size": 13, "family": "JetBrains Mono", "color": PLOTLY_FONT},
                    },
                    height=240,
                    margin={"t": 36, "b": 6, "l": 6, "r": 6},
                    paper_bgcolor=PLOTLY_PAPER,
                    plot_bgcolor=PLOTLY_PAPER,
                    font={"color": PLOTLY_FONT, "family": "IBM Plex Sans", "size": 12},
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

            st.caption(
                f"Correlacionados: **{summary_data.get('correlated_count', 0)}** · "
                f"Individuales: **{summary_data.get('individual_count', 0)}**"
            )

        with st.expander("📈 Más gráficos", expanded=False):
            if summary_data:
                by_type = summary_data.get("by_event_type", [])
                if by_type:
                    tl = [t["event_type"] for t in by_type[:8]]
                    tv = [t["count"] for t in by_type[:8]]
                    fig_t = go.Figure(
                        data=[
                            go.Bar(
                                x=tv,
                                y=tl,
                                orientation="h",
                                marker={"color": "#0891B2", "line": {"color": "#0E7490", "width": 1}},
                                hovertemplate="<b>%{y}</b><br>Eventos: %{x}<extra></extra>",
                            )
                        ]
                    )
                    fig_t.update_layout(
                        title={
                            "text": "Eventos por tipo",
                            "font": {"size": 13, "family": "JetBrains Mono", "color": PLOTLY_FONT},
                        },
                        height=260,
                        margin={"t": 36, "b": 6, "l": 4, "r": 8},
                        paper_bgcolor=PLOTLY_PAPER,
                        plot_bgcolor=PLOTLY_PAPER,
                        font={"color": PLOTLY_FONT, "family": "IBM Plex Sans", "size": 11},
                        yaxis={"autorange": "reversed", "tickfont": {"color": PLOTLY_FONT}},
                        xaxis={"gridcolor": PLOTLY_GRID, "tickfont": {"color": PLOTLY_FONT}},
                        bargap=0.28,
                    )
                    st.plotly_chart(fig_t, use_container_width=True)

                ts = summary_data.get("time_series", [])
                if ts:
                    fig_ts = go.Figure(
                        data=[
                            go.Scatter(
                                x=[t["hour"] for t in ts],
                                y=[t["count"] for t in ts],
                                mode="lines+markers",
                                line={"color": "#0891B2", "width": 2.5, "shape": "spline"},
                                marker={"size": 7, "color": "#0891B2"},
                                fill="tozeroy",
                                fillcolor="rgba(8,145,178,0.14)",
                                hovertemplate="<b>%{x}</b><br>Eventos: %{y}<extra></extra>",
                            )
                        ]
                    )
                    fig_ts.update_layout(
                        title={
                            "text": "Eventos por hora",
                            "font": {"size": 13, "family": "JetBrains Mono", "color": PLOTLY_FONT},
                        },
                        height=220,
                        margin={"t": 36, "b": 6, "l": 8, "r": 8},
                        paper_bgcolor=PLOTLY_PAPER,
                        plot_bgcolor=PLOTLY_PAPER,
                        font={"color": PLOTLY_FONT, "family": "IBM Plex Sans", "size": 11},
                        xaxis={"gridcolor": PLOTLY_GRID, "tickfont": {"color": PLOTLY_FONT}},
                        yaxis={"gridcolor": PLOTLY_GRID, "tickfont": {"color": PLOTLY_FONT}},
                    )
                    st.plotly_chart(fig_ts, use_container_width=True)

        st.divider()
        st.markdown("### Exportar")
        if st.session_state.get("events_list"):
            export_data = st.session_state.events_list
            buf = io.StringIO()
            w = csv.DictWriter(
                buf,
                fieldnames=[
                    "id",
                    "received_at",
                    "source_ip",
                    "severity",
                    "event_type",
                    "ai_explanation",
                    "analyzed",
                    "correlation_group",
                ],
            )
            w.writeheader()
            for ev in export_data:
                w.writerow(
                    {
                        "id": ev.get("id"),
                        "received_at": ev.get("received_at"),
                        "source_ip": ev.get("source_ip"),
                        "severity": ev.get("severity", ""),
                        "event_type": ev.get("event_type", ""),
                        "ai_explanation": ev.get("ai_explanation", ""),
                        "analyzed": ev.get("analyzed", False),
                        "correlation_group": ev.get("correlation_group", ""),
                    }
                )
            c1, c2 = st.columns(2)
            c1.download_button(
                "CSV",
                data=buf.getvalue().encode("utf-8"),
                file_name="eventos_ai_noc.csv",
                mime="text/csv",
                use_container_width=True,
            )
            c2.download_button(
                "JSON",
                data=json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="eventos_ai_noc.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.caption("Sin eventos en la página actual.")

        st.divider()
        st.markdown("### Reporte")
        report_source = st.radio(
            "Fuente", ["Eventos filtrados", "Último lote"], horizontal=True, key="report_src"
        )
        if st.button("Generar reporte", type="primary", use_container_width=True, key="gen_report"):
            with st.spinner("Generando..."):
                try:
                    params = (
                        {"limit": 500}
                        if report_source == "Eventos filtrados"
                        else {"limit": 50, "sort_by": "id", "sort_dir": "desc"}
                    )
                    items = (
                        httpx.get(f"{BACKEND_URL}/events", params=params, timeout=10, trust_env=False)
                        .json()
                        .get("items", [])
                    )
                    if not items:
                        st.info("No hay eventos.")
                    else:
                        sev_c: dict[str, int] = {}
                        typ_c: dict[str, int] = {}
                        an = cor = 0
                        for ev in items:
                            s = ev.get("severity") or "sin clasificar"
                            sev_c[s] = sev_c.get(s, 0) + 1
                            t = ev.get("event_type") or "sin clasificar"
                            typ_c[t] = typ_c.get(t, 0) + 1
                            if ev.get("analyzed"):
                                an += 1
                            if ev.get("correlation_group") is not None:
                                cor += 1
                        lines = [
                            "## Reporte — AI-NOC Copilot",
                            "",
                            f"**Total:** {len(items)} · **Analizados:** {an} · **Correlacionados:** {cor}",
                            "",
                            "### Severidad",
                        ]
                        for s, c in sorted(sev_c.items()):
                            lines.append(f"- **{s}:** {c}")
                        lines += ["", "### Tipo"]
                        for t, c in sorted(typ_c.items(), key=lambda x: -x[1]):
                            lines.append(f"- **{t}:** {c}")
                        lines += ["", "---", f"*{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*"]
                        text = "\n".join(lines)
                        st.markdown(text)
                        st.download_button(
                            "Descargar",
                            data=text.encode("utf-8"),
                            file_name="reporte_ai_noc.md",
                            mime="text/markdown",
                        )
                except httpx.HTTPError as exc:
                    st.error(f"Error: {exc}")

    with main_col:
        st.markdown("### Eventos recientes")

        # ── Panel de filtros armonizado (solo radios + text inputs) ──
        only_new = st.checkbox("Solo sin analizar", value=False, key="filt_only_new")

        # Fila 1: Severidad (radio fijo, no editable)
        sev_raw = st.radio(
            "Severidad",
            ["Todas", "low", "medium", "high"],
            horizontal=True,
            key="filt_sev",
        )
        sev_filter = "" if sev_raw == "Todas" else sev_raw

        # Fila 2: Buscar + Tipo (simétricos)
        t1, t2 = st.columns(2)
        with t1:
            search_q = st.text_input("Buscar en el log", placeholder="IP o texto…", key="filt_q")
        with t2:
            type_filter = st.text_input("Tipo de evento", placeholder="fuerza_bruta…", key="filt_type")

        # Fila 3: Ordenar (radio) — opciones fijas
        sort_label = st.radio(
            "Ordenar por",
            SORT_LABELS,
            horizontal=True,
            key="filt_sort",
        )

        # Fila 4: Dirección + Por página (radios alineados)
        r1, r2 = st.columns(2)
        with r1:
            sort_dir_label = st.radio(
                "Dirección",
                ["Descendente ↓", "Ascendente ↑"],
                horizontal=True,
                key="filt_dir",
            )
        with r2:
            page_size = st.radio(
                "Por página",
                [10, 25, 50],
                horizontal=True,
                key="filt_page_size",
                format_func=str,
            )

        # Fecha / ID compactos
        with st.expander("Fecha e ID", expanded=False):
            fd1, fd2, fd3, fd4 = st.columns(4)
            with fd1:
                date_from = st.date_input("Desde", value=None, format="DD/MM/YYYY", key="filt_df")
            with fd2:
                time_from = st.time_input("Hora", value=None, key="filt_tf", step=60)
            with fd3:
                date_to = st.date_input("Hasta", value=None, format="DD/MM/YYYY", key="filt_dt")
            with fd4:
                time_to = st.time_input("Hora ", value=None, key="filt_tt", step=60)
            id1, id2 = st.columns(2)
            with id1:
                id_from_raw = st.text_input("ID desde", placeholder="10", key="filt_idf")
            with id2:
                id_to_raw = st.text_input("ID hasta", placeholder="50", key="filt_idt")

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
            resp = httpx.get(f"{BACKEND_URL}/events", params=params, timeout=5, trust_env=False)
            payload = resp.json()
            if resp.status_code >= 400 or "items" not in payload:
                st.warning(f"Backend respondió {resp.status_code}.")
                events, total = [], 0
            else:
                events = payload["items"]
                total = payload["total"]
            st.session_state["total_cargado"] = total
            st.session_state["events_list"] = events
        except httpx.HTTPError:
            events, total = [], 0
            st.session_state["total_cargado"] = 0
            st.session_state["events_list"] = []
            st.error("Backend no disponible.")

        if not events:
            st.info("No hay eventos con estos filtros.")

        for event in events:
            with st.expander(_event_header(event)):
                st.code(event["raw_message"], language="text")
                if event.get("analyzed"):
                    st.markdown(
                        f"**Severidad:** {_severity_content_badge(event.get('severity'), True)}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Explicación IA:** {event.get('ai_explanation', '')}")
                    tk = f"analysis_time_{event['id']}"
                    if tk in st.session_state:
                        st.caption(f"⏱️ {st.session_state[tk]:.2f}s")
                else:
                    if st.button("Explicar con IA", key=f"analyze-{event['id']}", type="primary"):
                        with st.spinner("Consultando al modelo local..."):
                            import time as _t

                            t0 = _t.perf_counter()
                            try:
                                r = httpx.post(
                                    f"{BACKEND_URL}/events/{event['id']}/analyze",
                                    timeout=30,
                                    trust_env=False,
                                )
                                elapsed = _t.perf_counter() - t0
                                if r.status_code == 200:
                                    st.session_state[f"analysis_time_{event['id']}"] = elapsed
                                    st.rerun()
                                else:
                                    st.error(f"Error: {r.text}")
                            except httpx.ConnectError:
                                st.error("No se pudo conectar a Ollama.")
                            except httpx.TimeoutException:
                                st.error("Timeout (>30s).")

        total_pages = max(1, (total + page_size - 1) // page_size)
        prev_d = page == 0
        next_d = (page + 1) * page_size >= total
        p1, p2, p3, p4, p5, p6 = st.columns([1.1, 0.7, 1.1, 2.2, 1.1, 1.1])

        def _goto():
            v = st.session_state.get("go_to_page", "")
            if str(v).isdigit():
                st.session_state["events_page"] = max(1, min(int(v), total_pages)) - 1

        if p1.button("« Primera", disabled=prev_d, use_container_width=True, key="pg_f"):
            st.session_state["events_page"] = 0
            st.rerun()
        p2.text_input(
            "Pág",
            value=str(page + 1),
            max_chars=4,
            key="go_to_page",
            on_change=_goto,
            label_visibility="collapsed",
        )
        if p3.button("‹ Ant", disabled=prev_d, use_container_width=True, key="pg_p"):
            st.session_state["events_page"] = max(0, page - 1)
            st.rerun()
        desde = (page * page_size) + 1 if total else 0
        hasta = min((page + 1) * page_size, total)
        p4.markdown(
            f"<div style='text-align:center;padding-top:0.3rem;color:var(--ainoc-muted);"
            f"font-size:0.76rem;font-family:JetBrains Mono,monospace;'>"
            f"{desde}–{hasta} / {total} · {page + 1}/{total_pages}</div>",
            unsafe_allow_html=True,
        )
        if p5.button("Sig ›", disabled=next_d, use_container_width=True, key="pg_n"):
            st.session_state["events_page"] = page + 1
            st.rerun()
        if p6.button("Última »", disabled=(page >= total_pages - 1), use_container_width=True, key="pg_l"):
            st.session_state["events_page"] = total_pages - 1
            st.rerun()

# ── TAB CHAT ────────────────────────────────────────────────────────────────
with tab_chat:
    st.markdown("### Chat con el Copiloto")
    st.caption(
        "Indicá si consultás un evento o un grupo, escribí el número de ID y preguntá. "
        "El historial se conserva al cambiar de tema."
    )

    chat_dest = st.radio(
        "Tipo de consulta",
        ["Evento individual", "Grupo de correlación"],
        horizontal=True,
        key="chat_dest",
    )

    # ID numérico (columna estrecha para que no ocupe todo el ancho)
    id_label = (
        "ID del evento (solo número)" if chat_dest == "Evento individual" else "Nº de grupo de correlación"
    )
    id_col, _ = st.columns([1, 3])
    with id_col:
        if "chat_id_num" not in st.session_state:
            st.session_state.chat_id_num = 1
        selected_id = int(
            st.number_input(
                id_label,
                min_value=1,
                step=1,
                key="chat_id_num",
            )
        )

    # Reset historial solo si cambia el destino (tipo o id), NO al cambiar tema
    dest_key = f"{chat_dest}:{selected_id}"
    if st.session_state.get("chat_prev_dest") != dest_key:
        st.session_state.chat_messages = []
        st.session_state.chat_prev_dest = dest_key

    def _load_event_by_id(eid: int) -> dict | None:
        """Carga un evento por ID. Intenta GET /events/{id}; si no existe, lista filtrada."""
        try:
            r = httpx.get(f"{BACKEND_URL}/events/{eid}", timeout=5, trust_env=False)
            if r.status_code == 200:
                data = r.json()
                # Algunos backends envuelven en {"item": ...}
                if isinstance(data, dict) and "id" in data:
                    return data
                if isinstance(data, dict) and "item" in data:
                    return data["item"]
        except httpx.HTTPError:
            pass
        # Fallback: filtro por rango de ID en el listado
        try:
            r = httpx.get(
                f"{BACKEND_URL}/events",
                params={"id_from": eid, "id_to": eid, "limit": 5},
                timeout=5,
                trust_env=False,
            )
            if r.status_code == 200:
                payload = r.json()
                items = payload.get("items") if isinstance(payload, dict) else payload
                if isinstance(items, list):
                    for it in items:
                        if it.get("id") == eid:
                            return it
        except httpx.HTTPError:
            pass
        # Último recurso: página reciente y búsqueda local
        try:
            r = httpx.get(
                f"{BACKEND_URL}/events",
                params={"limit": 200, "sort_by": "id", "sort_dir": "desc"},
                timeout=8,
                trust_env=False,
            )
            if r.status_code == 200:
                payload = r.json()
                items = payload.get("items") if isinstance(payload, dict) else payload
                if isinstance(items, list):
                    for it in items:
                        if it.get("id") == eid:
                            return it
        except httpx.HTTPError:
            pass
        return None

    # Cargar contexto del ID indicado
    ctx_ok = False
    chips: list[str] = []
    if chat_dest == "Evento individual":
        data = _load_event_by_id(selected_id)
        if data:
            ctx_ok = True
            st.session_state["chat_events_cache"] = {
                selected_id: {
                    "severity": data.get("severity"),
                    "event_type": data.get("event_type"),
                    "ai_explanation": data.get("ai_explanation") or "",
                    "analyzed": data.get("analyzed", False),
                    "correlation_group": data.get("correlation_group"),
                    "raw_message": data.get("raw_message", ""),
                }
            }
            c = st.session_state["chat_events_cache"][selected_id]
            st.markdown(
                f'<div class="ainoc-context-card"><strong>Evento #{selected_id}</strong> · '
                f"Severidad: {c.get('severity') or '—'} · Tipo: {c.get('event_type') or '—'} · "
                f"Analizado: {'Sí' if c.get('analyzed') else 'No'}</div>",
                unsafe_allow_html=True,
            )
            sev = c.get("severity") or "?"
            chips = [
                f"¿Qué significa el evento #{selected_id}?",
                f"¿Es una amenaza real (sev: {sev})?",
                "¿Qué debo hacer ahora?",
                f"¿Por qué severidad '{sev}'?",
            ]
        else:
            st.warning(
                f"No se encontró el evento #{selected_id}. "
                "Comprobá el ID en la pestaña Eventos (número tras #)."
            )
    else:
        try:
            resp_gr = httpx.get(
                f"{BACKEND_URL}/events/correlation-history",
                timeout=5,
                trust_env=False,
            )
            groups = resp_gr.json().get("groups") or []

            if not groups:
                st.warning(
                    "No hay grupos en el histórico. Ve a la pestaña 'Correlación' y correlaciona eventos primero."
                )
                ctx_ok = False
            else:
                # Crear opciones legibles para el selectbox
                group_options = {
                    f"Grupo #{g['correlation_group']} ({g['event_count']} evt, {g.get('pattern', 'indeterminado')})": g[
                        "correlation_group"
                    ]
                    for g in groups
                }

                # Usar selectbox en lugar de number_input a ciegas
                selected_label = st.selectbox(
                    "Seleccionar grupo del histórico", list(group_options.keys()), key="chat_group_select"
                )
                selected_id = group_options[selected_label]

                found = next((g for g in groups if g["correlation_group"] == selected_id), None)
                if found:
                    ctx_ok = True
                    ips = ", ".join(found.get("attacker_ips") or [])
                    st.session_state["chat_groups_cache"] = {
                        selected_id: {
                            "ips": ips,
                            "pattern": found.get("pattern") or "indeterminado",
                            "severity": found.get("severity") or "low",
                            "event_count": found["event_count"],
                            "unique_ports": len(found.get("unique_ports") or []),
                        }
                    }
                    c = st.session_state["chat_groups_cache"][selected_id]
                    st.markdown(
                        f'<div class="ainoc-context-card"><strong>Grupo #{selected_id}</strong> · '
                        f"IP(s): {c['ips']} · Patrón: {c['pattern']} · "
                        f"{c['event_count']} evt · {c['unique_ports']} puertos</div>",
                        unsafe_allow_html=True,
                    )
                    chips = [
                        f"¿Qué significa el grupo #{selected_id}?",
                        f"¿Es una amenaza real el patrón '{c['pattern']}'?",
                        f"¿Qué debo hacer con {c['ips']}?",
                        f"¿Por qué se clasificó como '{c['pattern']}'?",
                    ]
        except httpx.HTTPError:
            st.warning("No se pudo cargar el histórico de correlación.")
    if ctx_ok:
        cc = st.columns(4)
        for i, q in enumerate(chips):
            with cc[i]:
                if st.button(q, key=f"chip_{i}", use_container_width=True):
                    st.session_state["chat_pending_msg"] = q
                    st.rerun()

    # ── Área de conversación: UN solo HTML con scroll (mensajes DENTRO) ──
    n_msg = len(st.session_state.chat_messages)
    chat_body = _render_chat_html(st.session_state.chat_messages)
    st.markdown(
        f'<div class="ainoc-chat-frame">'
        f'<div class="ainoc-chat-top">💬 Conversación · {n_msg} mensajes</div>'
        f'<div class="ainoc-chat-scroll">{chat_body}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.expander("📎 Adjuntar logs adicionales (opcional)", expanded=False):
        st.text_area(
            "Logs extra",
            height=60,
            placeholder="Pegá líneas de log…",
            key="chat_attach_widget",
            label_visibility="collapsed",
        )

    if prompt := st.chat_input("Escribí tu pregunta…"):
        st.session_state["chat_pending_msg"] = prompt
        st.rerun()

    pending = st.session_state.pop("chat_pending_msg", None)
    if pending and ctx_ok and selected_id is not None:
        user_message = pending
        attach = (st.session_state.get("chat_attach_widget") or "").strip()

        if chat_dest == "Evento individual":
            ev_c = st.session_state.get("chat_events_cache", {}).get(selected_id, {})
            user_message += (
                f"\n\n---\n**CONTEXTO DEL EVENTO #{selected_id} (usar SOLO esto):**\n"
                f"- Severidad: {ev_c.get('severity', 'sin analizar')}\n"
                f"- Tipo: {ev_c.get('event_type', 'sin clasificar')}\n"
                f"- Analizado: {'Sí' if ev_c.get('analyzed') else 'No'}\n"
                f"- Explicación previa: {(ev_c.get('ai_explanation') or 'ninguna')[:200]}\n"
                f"- Grupo: {ev_c.get('correlation_group', 'ninguno')}"
            )
        else:
            gr_c = st.session_state.get("chat_groups_cache", {}).get(selected_id, {})
            user_message += (
                f"\n\n---\n**CONTEXTO DEL GRUPO #{selected_id} (usar SOLO esto):**\n"
                f"- IP(s): {gr_c.get('ips', '?')}\n"
                f"- Patrón: {gr_c.get('pattern', 'indeterminado')}\n"
                f"- Severidad: {gr_c.get('severity', 'low')}\n"
                f"- Eventos: {gr_c.get('event_count', 0)}\n"
                f"- Puertos únicos: {gr_c.get('unique_ports', 0)}"
            )
        if attach:
            user_message += "\n\n---\n**Logs adicionales:**\n```\n" + attach + "\n```"

        st.session_state.chat_messages.append({"role": "user", "content": user_message})

        system_parts = [
            "Eres un analista SENIOR de seguridad de redes (copiloto NOC local).\n"
            "REGLAS: usa SOLO el CONTEXTO; no inventes IPs/puertos/patrones; "
            "respeta fuerza_bruta vs indeterminado; español técnico claro.\n"
            "FORMATO: Diagnóstico · Evidencia · Riesgo · Acción inmediata · Investigación adicional."
        ]
        try:
            if chat_dest == "Evento individual":
                ev_c = st.session_state.get("chat_events_cache", {}).get(selected_id, {})
                system_parts.append(f"Log: {ev_c.get('raw_message', '')}")
                if ev_c.get("analyzed"):
                    system_parts.append(
                        f"Análisis: sev={ev_c.get('severity')} tipo={ev_c.get('event_type')}. "
                        f"{ev_c.get('ai_explanation', '')}"
                    )
            else:
                gr_c = st.session_state.get("chat_groups_cache", {}).get(selected_id, {})
                system_parts.append(
                    f"Grupo #{selected_id}: IPs={gr_c.get('ips')} patrón={gr_c.get('pattern')} "
                    f"eventos={gr_c.get('event_count')} sev={gr_c.get('severity')}"
                )
        except Exception:
            system_parts.append("(sin contexto detallado)")

        with st.spinner("Consultando al modelo..."):
            import time as _time

            t0 = _time.perf_counter()
            chunks: list[str] = []
            try:
                with httpx.stream(
                    "POST",
                    f"{BACKEND_URL}/events/{selected_id}/chat",
                    json={"message": user_message, "history": st.session_state.chat_messages[:-1]},
                    timeout=120,
                    trust_env=False,
                ) as resp:
                    for chunk in resp.iter_text():
                        if chunk:
                            chunks.append(chunk)
            except httpx.HTTPError as exc:
                chunks.append(f"Error de conexión: {exc}")
            response = "".join(chunks)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            st.session_state["chat_last_elapsed"] = _time.perf_counter() - t0
            st.rerun()

    if st.session_state.get("chat_last_elapsed") and st.session_state.chat_messages:
        st.caption(f"⏱️ Última respuesta: {st.session_state['chat_last_elapsed']:.1f}s")

# ── TAB CORRELACIÓN ─────────────────────────────────────────────────────────
with tab_corr:
    st.markdown("### Correlación de eventos")
    if st.button("Correlacionar eventos sin analizar", type="primary", key="btn_correlate"):
        with st.spinner("Buscando patrones..."):
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
                st.error(f"Error: {exc}")
                correlation = None
        if correlation:
            if correlation["groups_detected"] == 0:
                st.info("No se detectaron patrones por encima del umbral.")
            else:
                st.success(f"{correlation['groups_detected']} patrón(es) detectado(s)")
                for group in correlation["groups"]:
                    icon = "🚨" if group["severity"] == "high" else "⚠️"
                    with st.expander(
                        f"{icon} {group['attacker_ip']} — {group['event_type']} ({group['event_count']} evt.)"
                    ):
                        st.markdown(f"**Severidad:** `{group['severity']}`")
                        st.markdown(f"**Explicación:** {group['explanation']}")
                        st.markdown(f"**Acción:** {group['recommended_action']}")
                        with st.popover("IDs"):
                            st.caption(", ".join(map(str, group["event_ids"])))
                st.rerun()

    st.divider()
    st.markdown("### Histórico de correlación")
    if st.button("Actualizar histórico", key="refresh_history"):
        st.rerun()
    try:
        history = httpx.get(
            f"{BACKEND_URL}/events/correlation-history",
            timeout=10,
            trust_env=False,
        ).json()
    except httpx.HTTPError:
        history = {"total_groups": 0, "groups": []}

    groups = history.get("groups") or []
    if not groups:
        st.caption("Sin grupos registrados.")
    else:
        st.caption(f"{history.get('total_groups', len(groups))} grupo(s)")
        for g in groups:
            pattern = g.get("pattern")
            icon = PATTERN_ICONS.get(pattern, "❓")
            ips = ", ".join(g.get("attacker_ips") or [])
            sev = g.get("severity") or "low"
            first = (g.get("first_seen") or "")[:16].replace("T", " ")
            last = (g.get("last_seen") or "")[:16].replace("T", " ")
            with st.expander(
                f"{icon} #{g['correlation_group']} · {ips} ({g['event_count']} evt) · {pattern or 'indeterminado'}"
            ):
                st.markdown(
                    f"**Severidad:** {_severity_content_badge(sev)} · "
                    f"**Puertos únicos:** {len(g.get('unique_ports') or [])}",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Ventana:** {first} → {last}")
                with st.popover("IDs"):
                    st.caption(", ".join(map(str, g.get("event_ids") or [])))


# ── TAB RENDIMIENTO ──────────────────────────────────────────────────────────
with tab_perf:
    st.markdown("### ⚡ Rendimiento del Motor LLM y Hardware")
    st.caption("Análisis de latencia, uso de hardware (GPU/CPU) y comparativa de trade-offs para el proyecto final.")

    perf_data = None
    try:
        perf_resp = httpx.get(f"{BACKEND_URL}/performance/stats", timeout=5, trust_env=False)
        if perf_resp.status_code == 200:
            perf_data = perf_resp.json()
    except httpx.HTTPError:
        pass

    if not perf_data:
        st.warning("No se pudo conectar al endpoint de rendimiento del backend.")
    else:
        hw = perf_data.get("hardware_info", {})
        summary_p = perf_data.get("summary", {})
        history_p = perf_data.get("history", [])
        trade_offs = perf_data.get("trade_offs", [])

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Hardware", hw.get("gpu", "GPU"), hw.get("architecture", ""))
        col2.metric("Modelo Activo", hw.get("current_model", ""), hw.get("model_memory", ""))
        col3.metric("Promedio Inferencia", f"{summary_p.get('avg_generation_seconds', 0)}s", f"{summary_p.get('avg_tokens_per_second', 0)} tok/s")
        col4.metric("Llamadas Totales", summary_p.get("total_calls", 0), f"Promedio total: {summary_p.get('avg_total_seconds', 0)}s")

        st.divider()

        # Diagnóstico de Hardware y Cuello de Botella
        c_left, c_right = st.columns([1.2, 1], gap="medium")

        with c_left:
            st.markdown("#### 🔍 Diagnóstico Físico & Cuello de Botella")
            st.markdown(
                f"""
- **Distribución de Carga (Offload):** `{hw.get('offload_split', '74% CPU / 26% GPU')}`.
- **Límite de VRAM:** La tarjeta gráfica **{hw.get('gpu')}** cuenta con **2 GB de VRAM**, mientras que el modelo actual pesa **~2.4 GB** en memoria.
- **Causa Raíz:** Al no caber por completo en la VRAM, Ollama descarga ~74% de las capas a la CPU del sistema, lo que reduce la velocidad de generación a ~5 tok/s (~19s por respuesta).
- **Determinismo vs IA:** Recordar que la detección de amenazas (beaconing, entropía DGA, escaneos) es **100% determinista** en Python. El LLM actúa únicamente como sintetizador y explicador, por lo que una menor velocidad de inferencia no afecta la precisión de detección.
                """
            )

        with c_right:
            st.markdown("#### ⚖️ Comparativa de Trade-offs y Opciones")
            for item in trade_offs:
                badge = "⭐ RECOMENDADO" if item.get("recommended") else "⚪ Alternativa"
                border_color = "#0891B2" if item.get("recommended") else "#334155"
                st.markdown(
                    f"""
<div style="background: var(--ainoc-panel); border: 1px solid {border_color}; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;">
    <strong>{item['option']}</strong> <span style="font-size: 0.75rem; float: right; color: var(--ainoc-muted);">{badge}</span><br>
    <small style="color: var(--ainoc-accent);">VRAM: {item['vram']} · Velocidad: {item['speed']}</small><br>
    <span style="font-size: 0.82rem;">{item['description']}</span>
</div>
                    """,
                    unsafe_allow_html=True,
                )

        st.divider()

        # Gráficos de latencia temporal
        st.markdown("#### 📈 Historial Dinámico de Tiempos de Respuesta")
        if not history_p:
            st.info("Aún no hay llamadas registradas en la base de datos. Generá eventos o realiza consultas para alimentar las estadísticas.")
        else:
            import plotly.graph_objects as go

            timestamps = [h["timestamp"][11:19] for h in history_p]
            gen_secs = [h["gen_seconds"] for h in history_p]

            fig_perf = go.Figure()
            fig_perf.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=gen_secs,
                    mode="lines+markers",
                    name="Generación (s)",
                    line={"color": "#0891B2", "width": 2},
                )
            )
            fig_perf.update_layout(
                title={
                    "text": "Tiempo de Generación por Inferencia (Segundos)",
                    "font": {"size": 13, "family": "JetBrains Mono", "color": PLOTLY_FONT},
                },
                height=260,
                margin={"t": 36, "b": 24, "l": 24, "r": 24},
                paper_bgcolor=PLOTLY_PAPER,
                plot_bgcolor=PLOTLY_PAPER,
                font={"color": PLOTLY_FONT, "family": "IBM Plex Sans", "size": 12},
                xaxis={"gridcolor": PLOTLY_GRID},
                yaxis={"gridcolor": PLOTLY_GRID, "title": "Segundos"},
                showlegend=False,
            )
            st.plotly_chart(fig_perf, use_container_width=True)

            with st.expander("📋 Ver registro tabular de llamadas recientes", expanded=False):
                st.dataframe(
                    [
                        {
                            "ID": h["id"],
                            "Hora": h["timestamp"].replace("T", " ")[:19],
                            "Modo": h["mode"],
                            "Total (s)": round(h["total_seconds"], 2),
                            "Carga (s)": round(h["load_seconds"], 2),
                            "Eval Prompt (s)": round(h["prompt_eval_seconds"], 2),
                            "Gen (s)": round(h["gen_seconds"], 2),
                            "Tokens Gen": h["gen_tokens"],
                            "Tok/s": round(h["tokens_per_second"], 1),
                        }
                        for h in history_p
                    ],
                    use_container_width=True,
                )

# ── TAB ACERCA DEL PROYECTO ───────────────────────────────────────────────────
with tab_about:
    st.markdown("### Acerca del proyecto")

    # ── Sección: El problema ──
    st.markdown("#### El problema")
    st.markdown(
        """
Administrador de red de una empresa con arquitectura hub-and-spoke (sucursales con pfSense → sede central), red **air-gapped** (sin acceso a Internet). Revisar logs de firewall manualmente es lento y no escala. El LLM en la nube no es una opción (ni por política, ni por falta de Internet).
        """
    )

    # ── Sección: Arquitectura ──
    st.markdown("#### Arquitectura")
    arch_img_path = "docs/diagrams/arquitectura.png"
    try:
        st.image(arch_img_path, caption="Arquitectura del sistema")
    except Exception:
        st.info(f"📐 Diagrama de arquitectura pendiente — se generará en Fase 3 del plan. Ruta esperada: `{arch_img_path}`")

    # ── Sección: Decisiones de diseño clave ──
    st.markdown("#### Decisiones de diseño clave")

    decisions = [
        {
            "title": "Ollama nativo, no en Docker",
            "desc": "Ollama corre en el host (no en contenedor) para evitar duplicar el modelo (~2.1 GB) y simplificar networking. Docker solo para backend+frontend en el entregable del curso (SPEC §3).",
        },
        {
            "title": "Detección determinista, LLM solo explica",
            "desc": "Beaconing (CV de intervalos) y DGA (entropía Shannon) se detectan en Python puro. El LLM recibe el hallazgo ya clasificado y redacta la explicación — nunca decide si algo es malicioso (AGENTS §11, SPEC §11).",
        },
        {
            "title": "IP atacante se extrae del raw_message",
            "desc": "`NetworkEvent.source_ip` es la IP del paquete UDP (el propio pfSense). La IP real del atacante se extrae con regex del `raw_message` (`extract_attacker_ip` en `main.py:46`). No cambiar a `source_ip` (AGENTS §11).",
        },
        {
            "title": "Contrato LLM inmutable (4 claves JSON)",
            "desc": "Salida estricta: `severity`, `event_type`, `explanation`, `recommended_action`. Prompt en `backend/app/prompts/threat_explainer.txt`, `format=json`, `temperature=0.1`. Cambiarlo rompe `main.py` (SPEC §6, §11).",
        },
    ]

    for d in decisions:
        with st.expander(d["title"], expanded=False):
            st.markdown(d["desc"])

    # ── Sección: Stack técnico ──
    st.markdown("#### Stack técnico")
    st.markdown(
        """
<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
  <span style="background: var(--ainoc-accent); color: #0B1220; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">FastAPI</span>
  <span style="background: var(--ainoc-success); color: #0B1220; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">SQLModel</span>
  <span style="background: var(--ainoc-warning); color: #0B1220; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">SQLite</span>
  <span style="background: var(--ainoc-accent-dim); color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">Streamlit</span>
  <span style="background: #8B5CF6; color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">Ollama + Qwen 3B</span>
  <span style="background: var(--ainoc-danger); color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">Plotly</span>
</div>
        """,
        unsafe_allow_html=True,
    )

    # ── Sección: Roadmap ──
    st.markdown("#### Roadmap")
    phases = [
        {"name": "Fase 0 — Diseño y alcance", "status": "done", "progress": 100},
        {"name": "Fase 1 — Ingesta y pipeline base", "status": "done", "progress": 100},
        {"name": "Fase 2 — LLM local", "status": "done", "progress": 100},
        {"name": "Fase 3 — Datos sintéticos y verificación", "status": "done", "progress": 100},
        {"name": "Fase 4 — Correlación de eventos", "status": "done", "progress": 100},
        {"name": "Fase 5.5 — Detección extendida", "status": "done", "progress": 100},
        {"name": "Fase 5.6 — Ingesta manual de logs", "status": "in_progress", "progress": 80},
        {"name": "Fase 5.7 — Búsqueda, filtros y paginación", "status": "done", "progress": 100},
        {"name": "Fase 5.8 — Persistencia y clasificación de correlación", "status": "done", "progress": 100},
        {"name": "Fase 5.9 — Estadísticas y gráficos", "status": "done", "progress": 100},
        {"name": "Fase 5.10 — Chat interactivo y Rendimiento", "status": "done", "progress": 100},
        {"name": "Fase 6 — Documentación y entrega", "status": "pending", "progress": 30},
    ]

    for p in phases:
        col1, col2 = st.columns([3.5, 1.5])
        with col1:
            st.markdown(f"**{p['name']}**")
        with col2:
            if p["status"] == "done":
                st.markdown('<span class="ainoc-badge-low">✓ Completada</span>', unsafe_allow_html=True)
            elif p["status"] == "in_progress":
                st.markdown('<span class="ainoc-badge-medium">⟳ En progreso</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span style="color: var(--ainoc-muted); font-size: 0.7rem; font-family: JetBrains Mono, monospace;">⬜ Pendiente</span>', unsafe_allow_html=True)
        st.progress(p["progress"] / 100)

    st.markdown("")
    st.link_button("🔗 Ver en GitHub", "https://github.com/0xmarcosdev/ai-noc-copilot", use_container_width=True)
