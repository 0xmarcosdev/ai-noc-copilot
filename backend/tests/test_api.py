"""
Tests mínimos para cumplir el requisito de testing del curso:
- Se puede crear y leer un NetworkEvent en una BD SQLite en memoria.
- El endpoint /events lista eventos correctamente.
- El endpoint /events/{id}/analyze maneja bien un Ollama caído (mock).

Correr con: pytest backend/tests -v
"""
import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.gettempdir(), "ai_noc_test.db")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.main import app, engine
from app.models import NetworkEvent

SQLModel.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def seed_event():
    with Session(engine) as session:
        event = NetworkEvent(
            source_ip="192.168.1.1",
            raw_message="Oct 10 12:00:00 pfSense filterlog: block,,,em0,192.168.1.50,80",
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        yield event


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_events(seed_event):
    client = TestClient(app)
    resp = client.get("/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert events[0]["source_ip"] == "192.168.1.1"


def test_analyze_missing_event_returns_404():
    client = TestClient(app)
    resp = client.post("/events/999999/analyze")
    assert resp.status_code == 404


def test_analyze_event_ollama_down(monkeypatch, seed_event):
    """Si Ollama no responde, el endpoint debe devolver 502, no 500."""
    from app import main as main_module

    async def fake_explain_event(log_raw: str):
        from app.llm_service import LLMAnalysisError
        raise LLMAnalysisError("Ollama no respondió (simulado en test)")

    monkeypatch.setattr(main_module, "explain_event", fake_explain_event)

    client = TestClient(app)
    resp = client.post(f"/events/{seed_event.id}/analyze")
    assert resp.status_code == 502
