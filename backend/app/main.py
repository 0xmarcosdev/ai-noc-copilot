import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from app.llm_service import LLMAnalysisError, explain_event
from app.models import NetworkEvent
from app.syslog_listener import start_syslog_listener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-noc")

DB_PATH = os.getenv("DB_PATH", "./data/events.db")
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", "5514"))

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


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


@app.get("/summary")
def summary(hours: int = 24):
    """Resumen simple para el chat del dashboard ('¿qué pasó hoy?')."""
    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent).where(NetworkEvent.analyzed == True)  # noqa: E712
        ).all()
        by_severity: dict[str, int] = {}
        for e in events:
            by_severity[e.severity or "low"] = by_severity.get(e.severity or "low", 0) + 1
        return {"total_analyzed": len(events), "by_severity": by_severity}
