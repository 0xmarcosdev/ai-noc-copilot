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


def _seed_bruteforce_batch(attacker_ip: str, count: int):
    with Session(engine) as session:
        for i in range(count):
            event = NetworkEvent(
                source_ip="127.0.0.1",
                raw_message=(
                    f"Aug 16 00:00:{i:02d} pfsense-prod filterlog: 1,,,{1000000000 + i},em0,"
                    f"match,block,in,4,0x0,,64,{1000 + i},0,DF,6,tcp,50,"
                    f"{attacker_ip},192.168.10.5,{40000 + i},22,0,S,1,,65535,,mss"
                ),
            )
            session.add(event)
        session.commit()


def test_correlate_groups_events_by_attacker_ip(monkeypatch):
    """Un grupo que alcanza el umbral se envía al LLM UNA vez y se marca analizado."""
    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        return {
            "severity": "high",
            "event_type": "fuerza bruta ssh",
            "explanation": "patrón de prueba: mismo origen, mismo puerto, repetido",
            "recommended_action": "bloquear ip",
        }

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    attacker_ip = "203.0.113.77"
    _seed_bruteforce_batch(attacker_ip, count=6)

    client = TestClient(app)
    resp = client.post("/events/correlate", params={"window_minutes": 10, "threshold": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["groups_detected"] == 1
    assert data["groups"][0]["attacker_ip"] == attacker_ip
    assert data["groups"][0]["event_count"] == 6
    assert data["groups"][0]["severity"] == "high"

    # Los eventos del grupo deben quedar marcados como analizados.
    with Session(engine) as session:
        updated = session.get(NetworkEvent, data["groups"][0]["event_ids"][0])
        assert updated.analyzed is True
        assert updated.severity == "high"


def test_correlate_ignores_groups_below_threshold(monkeypatch):
    """Un grupo por debajo del umbral no debe ni siquiera llamar al LLM."""
    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        raise AssertionError("no debería llamarse al LLM si no se alcanza el umbral")

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    attacker_ip = "203.0.113.88"
    _seed_bruteforce_batch(attacker_ip, count=2)  # por debajo del default (5)

    client = TestClient(app)
    resp = client.post("/events/correlate", params={"window_minutes": 10})
    assert resp.status_code == 200
    assert resp.json()["groups_detected"] == 0


def test_extract_attacker_ip():
    """La extracción de IP debe leer el campo srcip real, no source_ip del paquete UDP."""
    from app.main import extract_attacker_ip

    raw = ("Aug 16 00:00:00 pfsense-prod filterlog: 1,,,1000000000,em0,match,block,in,4,"
           "0x0,,64,1000,0,DF,6,tcp,50,203.0.113.77,192.168.10.5,40000,22,0,S,1,,65535,,mss")
    assert extract_attacker_ip(raw) == "203.0.113.77"
    assert extract_attacker_ip("openvpn[1]: Inactivity timeout, restarting") is None