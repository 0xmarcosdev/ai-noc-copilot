import logging
import os
import re
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # carga backend/.env si existe -- evita usar export/set a mano en cada terminal

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from app.llm_service import LLMAnalysisError, explain_correlated_events, explain_event
from app.models import NetworkEvent
from app.syslog_listener import start_syslog_listener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-noc")

DB_PATH = Path(os.getenv("DB_PATH", "./data/events.db")).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # SQLite no crea la carpeta contenedora sola
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", "5514"))
CORRELATION_THRESHOLD = int(os.getenv("CORRELATION_THRESHOLD", "5"))

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

# Extrae la IP origen REAL (el atacante) desde el CSV de filterlog.
# OJO: NetworkEvent.source_ip es la IP que envió el paquete UDP de syslog
# (el propio pfSense), NO la IP del atacante -- por eso correlacionamos
# usando esta extracción del raw_message, no la columna source_ip.
# Ver SPEC.md §4 y §7.
FILTERLOG_IPV4_RE = re.compile(
    r"filterlog:\s*\d+,,[^,]*,\d+,[^,]+,\w+,\w+,\w+,4,"
    r"[^,]*,[^,]*,\d+,\d+,\d+,\w+,\d+,\w+,"
    r"\d+,(?P<srcip>[\d.]+),(?P<dstip>[\d.]+),"
    r"(?P<srcport>\d+),(?P<dstport>\d+)"
)


def extract_attacker_ip(raw_message: str) -> Optional[str]:
    match = FILTERLOG_IPV4_RE.search(raw_message)
    return match.group("srcip") if match else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    transport = await start_syslog_listener(engine, host="0.0.0.0", port=SYSLOG_PORT)
    yield
    transport.close()


app = FastAPI(title="AI-NOC Copilot", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/events")
def list_events(limit: int = 50, only_unanalyzed: bool = False):
    with Session(engine) as session:
        query = select(NetworkEvent).order_by(NetworkEvent.received_at.desc()).limit(limit)
        if only_unanalyzed:
            query = query.where(NetworkEvent.analyzed == False)  # noqa: E712
        return session.exec(query).all()


@app.post("/events/{event_id}/analyze")
async def analyze_event(event_id: int):
    """
    Envía un evento al LLM local (Ollama) y guarda la explicación.
    Este es el endpoint "Explicar con IA" del dashboard.
    """
    with Session(engine) as session:
        event = session.get(NetworkEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Evento no encontrado")

        try:
            result = await explain_event(event.raw_message)
        except LLMAnalysisError as exc:
            logger.error("Fallo al analizar evento %s: %s", event_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        event.severity = result["severity"]
        event.event_type = result["event_type"]
        event.ai_explanation = f"{result['explanation']} Acción recomendada: {result['recommended_action']}"
        event.analyzed = True
        session.add(event)
        session.commit()
        session.refresh(event)
        return event


@app.post("/events/correlate")
async def correlate_events(window_minutes: int = 10, threshold: int = CORRELATION_THRESHOLD):
    """
    Agrupa eventos SIN ANALIZAR por IP atacante (extraída del raw_message,
    no de source_ip -- ver comentario junto a extract_attacker_ip) dentro
    de una ventana de tiempo. Si un grupo alcanza el umbral, se envían
    todos juntos al LLM en un solo prompt para que evalúe el patrón
    (ej. fuerza bruta), en vez de analizar cada evento aislado.
    Resuelve la limitación documentada en SPEC.md §7.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent)
            .where(NetworkEvent.analyzed == False)  # noqa: E712
            .where(NetworkEvent.received_at >= cutoff)
        ).all()

        groups: dict[str, list[NetworkEvent]] = defaultdict(list)
        for event in events:
            attacker_ip = extract_attacker_ip(event.raw_message)
            if attacker_ip:
                groups[attacker_ip].append(event)

    results = []
    for attacker_ip, group_events in groups.items():
        if len(group_events) < threshold:
            continue

        combined_log = "\n".join(e.raw_message for e in group_events)
        try:
            result = await explain_correlated_events(combined_log, count=len(group_events))
        except LLMAnalysisError as exc:
            logger.error("Fallo al correlacionar grupo %s: %s", attacker_ip, exc)
            continue

        event_ids = [e.id for e in group_events]
        with Session(engine) as session:
            for event_id in event_ids:
                db_event = session.get(NetworkEvent, event_id)
                db_event.severity = result["severity"]
                db_event.event_type = f"patrón correlacionado: {result['event_type']}"
                db_event.ai_explanation = result["explanation"]
                db_event.analyzed = True
                session.add(db_event)
            session.commit()

        results.append({
            "attacker_ip": attacker_ip,
            "event_count": len(group_events),
            "event_ids": event_ids,
            **result,
        })

    return {"window_minutes": window_minutes, "threshold": threshold, "groups_detected": len(results), "groups": results}


@app.get("/summary")
def summary(hours: int = 24):
    """Resumen simple para el chat del dashboard ('¿qué pasó hoy?')."""
    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent).where(NetworkEvent.analyzed == True)  # noqa: E712
        ).all()
        by_severity: dict[str, int] = {}
        high_severity_types: dict[str, int] = {}
        for e in events:
            sev = e.severity or "low"
            by_severity[sev] = by_severity.get(sev, 0) + 1
            if sev == "high" and e.event_type:
                high_severity_types[e.event_type] = high_severity_types.get(e.event_type, 0) + 1

        top_high_categories = sorted(high_severity_types.items(), key=lambda kv: kv[1], reverse=True)[:3]

        return {
            "total_analyzed": len(events),
            "by_severity": by_severity,
            "top_high_severity_types": [{"event_type": t, "count": c} for t, c in top_high_categories],
        }