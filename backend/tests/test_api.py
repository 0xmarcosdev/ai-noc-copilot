"""
Tests mínimos para cumplir el requisito de testing del curso:
- Se puede crear y leer un NetworkEvent en una BD SQLite en memoria.
- El endpoint /events lista eventos correctamente.
- El endpoint /events/{id}/analyze maneja bien un Ollama caído (mock).

Correr con: pytest backend/tests -v
"""
import os
import tempfile

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ai_noc_test.db")
os.environ["DB_PATH"] = _TEST_DB_PATH

# Sin esto, eventos de una corrida anterior de pytest quedan en el archivo
# temporal y contaminan los conteos exactos de /correlate, /detect-beaconing
# y /detect-suspicious-dns (bug real encontrado por OpenCode, 17 ago 2026).
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

import pytest
from app.main import app, engine
from app.models import NetworkEvent
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

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
    data = resp.json()
    assert "items" in data and "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["source_ip"] == "192.168.1.1"
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_list_events_pagination_and_filters():
    """Paginación (limit/offset) + filtros q / severity / only_unanalyzed / event_type."""
    with Session(engine) as session:
        session.add(NetworkEvent(
            source_ip="10.0.0.1",
            raw_message="filterlog block from 203.0.113.50 to internal",
            severity="high",
            event_type="fuerza bruta SSH",
            analyzed=True,
        ))
        session.add(NetworkEvent(
            source_ip="10.0.0.2",
            raw_message="filterlog pass out to 8.8.8.8",
            severity="low",
            event_type="trafico normal",
            analyzed=True,
        ))
        session.add(NetworkEvent(
            source_ip="10.0.0.3",
            raw_message="sin analizar todavia 203.0.113.99",
            analyzed=False,
        ))
        session.commit()

    client = TestClient(app)

    # Búsqueda por texto en raw_message
    resp = client.get("/events", params={"q": "203.0.113.50"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all("203.0.113.50" in e["raw_message"] for e in data["items"])

    # Filtro por severidad
    resp = client.get("/events", params={"severity": "high"})
    data = resp.json()
    assert data["total"] >= 1
    assert all(e["severity"] == "high" for e in data["items"])

    # Solo sin analizar
    resp = client.get("/events", params={"only_unanalyzed": True})
    data = resp.json()
    assert data["total"] >= 1
    assert all(e["analyzed"] is False for e in data["items"])

    # Paginación: limit=1 debe devolver un solo item y total > 1
    resp = client.get("/events", params={"limit": 1, "offset": 0})
    data = resp.json()
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert data["total"] >= 2

    resp2 = client.get("/events", params={"limit": 1, "offset": 1})
    data2 = resp2.json()
    assert data2["offset"] == 1
    assert len(data2["items"]) == 1
    assert data["items"][0]["id"] != data2["items"][0]["id"]

    # event_type parcial
    resp = client.get("/events", params={"event_type": "fuerza bruta"})
    data = resp.json()
    assert data["total"] >= 1
    assert all("fuerza bruta" in (e.get("event_type") or "") for e in data["items"])


def test_list_events_id_range_filter():
    """Filtro por rango de IDs (id_from/id_to) y por ID único (rango cerrado)."""
    with Session(engine) as session:
        created = []
        for i in range(3):
            event = NetworkEvent(source_ip="192.0.2.50", raw_message=f"evento rango id {i}")
            session.add(event)
            session.commit()
            session.refresh(event)
            created.append(event.id)

    client = TestClient(app)

    # Rango que cubre solo el segundo y tercer evento
    resp = client.get("/events", params={"id_from": created[1], "id_to": created[2]})
    assert resp.status_code == 200
    ids = [e["id"] for e in resp.json()["items"]]
    assert all(created[1] <= eid <= created[2] for eid in ids)
    assert created[0] not in ids

    # Rango cerrado de un solo ID -> exactamente ese evento
    resp = client.get("/events", params={"id_from": created[1], "id_to": created[1]})
    assert [e["id"] for e in resp.json()["items"]] == [created[1]]

    # Rango invertido (from > to) -> consulta vacía, no error
    resp = client.get("/events", params={"id_from": created[2], "id_to": created[0]})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_events_date_range_filter():
    """Filtro por ventana de received_at (naive UTC, como el resto del proyecto)."""
    from datetime import datetime, timedelta

    base = datetime.utcnow()
    with Session(engine) as session:
        events = {}
        for name in ("viejo", "medio", "futuro"):
            e = NetworkEvent(source_ip="192.0.2.60", raw_message=f"evento {name} fecha")
            session.add(e)
            session.commit()
            session.refresh(e)
            events[name] = e.id  # capturar el id DENTRO de la sesión (tras commit la instancia queda detached)
        offsets = {"viejo": -10, "medio": -5, "futuro": 10}
        for name, days in offsets.items():
            db_event = session.get(NetworkEvent, events[name])
            db_event.received_at = base + timedelta(days=days)
            session.add(db_event)
        session.commit()
    mid_id = events["medio"]

    client = TestClient(app)
    # Ventana [-7d, -3d] alrededor de base: contiene SOLO el evento del medio
    # (los demás eventos de la BD compartida están cerca de utcnow).
    resp = client.get(
        "/events",
        params={
            "received_at_from": (base - timedelta(days=7)).isoformat(),
            "received_at_to": (base - timedelta(days=3)).isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert [e["id"] for e in data["items"]] == [mid_id]

    # Solo límite inferior: debe incluir el futuro pero no el viejo
    resp = client.get("/events", params={"received_at_from": (base + timedelta(days=9)).isoformat()})
    ids = [e["id"] for e in resp.json()["items"]]
    assert events["futuro"] in ids
    assert events["viejo"] not in ids


def test_list_events_sort_params():
    """sort_by/sort_dir ordenan por el campo pedido; valor inválido -> 422."""
    with Session(engine) as session:
        for sev in ("low", "high", "medium"):
            session.add(NetworkEvent(
                source_ip="192.0.2.70",
                raw_message=f"evento sort {sev}",
                severity=sev,
                event_type="tipo sort",
                analyzed=True,
            ))
        session.commit()

    client = TestClient(app)

    # Orden por id ascendente y descendente
    resp = client.get("/events", params={"q": "evento sort", "sort_by": "id", "sort_dir": "asc"})
    ids = [e["id"] for e in resp.json()["items"]]
    assert len(ids) == 3
    assert ids == sorted(ids)

    resp = client.get("/events", params={"q": "evento sort", "sort_by": "id", "sort_dir": "desc"})
    ids_desc = [e["id"] for e in resp.json()["items"]]
    assert ids_desc == sorted(ids_desc, reverse=True)

    # Orden por severidad ascendente: high < low < medium (orden alfabético)
    resp = client.get("/events", params={"q": "evento sort", "sort_by": "severity", "sort_dir": "asc"})
    sevs = [e["severity"] for e in resp.json()["items"]]
    assert sevs == ["high", "low", "medium"]

    # Valor fuera del contrato -> 422 (validación de Literal en FastAPI)
    resp = client.get("/events", params={"sort_by": "raw_message"})
    assert resp.status_code == 422
    resp = client.get("/events", params={"sort_dir": "lateral"})
    assert resp.status_code == 422


def test_list_events_empty_string_params_are_tolerated():
    """Strings vacíos en params opcionales se tratan como None (no 422)."""
    client = TestClient(app)
    resp = client.get("/events", params={
        "id_from": "",
        "id_to": "",
        "received_at_from": "",
        "received_at_to": "",
        "q": "",
        "severity": "",
    })
    assert resp.status_code == 200
    assert "items" in resp.json()


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


def _raw_message_with_attacker_ip(ip: str, tag: int) -> str:
    return (
        f"Aug 16 00:00:{tag:02d} pfsense-prod filterlog: 1,,,10000000{tag:02d},em0,match,block,in,4,"
        f"0x0,,64,{tag},0,DF,6,tcp,60,{ip},192.168.10.5,4000{tag},22,0,S,1,,65535,,mss;nop;wscale"
    )


def test_correlate_groups_by_attacker_ip(monkeypatch):
    """Varios eventos de la misma IP atacante dentro de la ventana -> un solo grupo, severity alta."""
    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        return {
            "severity": "high",
            "event_type": "fuerza bruta SSH",
            "explanation": "Multiples intentos desde la misma IP en poco tiempo.",
            "recommended_action": "Bloquear la IP origen.",
        }

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    with Session(engine) as session:
        for i in range(6):
            session.add(NetworkEvent(
                source_ip="192.0.2.1",
                raw_message=_raw_message_with_attacker_ip("203.0.113.200", i),
            ))
        session.commit()

    client = TestClient(app)
    resp = client.post("/events/correlate", params={"window_minutes": 10, "threshold": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["groups_detected"] == 1
    assert data["groups"][0]["attacker_ip"] == "203.0.113.200"
    assert data["groups"][0]["event_count"] == 6
    assert data["groups"][0]["severity"] == "high"


def test_correlate_below_threshold_returns_no_groups():
    """Un solo evento no alcanza el umbral -> no se marca ningun grupo."""
    with Session(engine) as session:
        session.add(NetworkEvent(
            source_ip="192.0.2.1",
            raw_message=_raw_message_with_attacker_ip("198.51.100.9", 0),
        ))
        session.commit()

    client = TestClient(app)
    resp = client.post("/events/correlate", params={"window_minutes": 10, "threshold": 5})
    assert resp.status_code == 200
    assert resp.json()["groups_detected"] == 0


def test_correlate_ignores_groups_below_threshold(monkeypatch):
    """Un grupo por debajo del umbral no debe ni siquiera llamar al LLM."""
    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        raise AssertionError("no debería llamarse al LLM si no se alcanza el umbral")

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    with Session(engine) as session:
        for i in range(2):  # por debajo del default (5)
            session.add(NetworkEvent(
                source_ip="192.0.2.1",
                raw_message=_raw_message_with_attacker_ip("203.0.113.88", i),
            ))
        session.commit()

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


def _pass_out_message(src: str, dst: str, dport: int, tag: int) -> str:
    return (
        f"Aug 17 00:00:{tag:02d} pfsense-prod filterlog: 1,,,10000000{tag:02d},igb0,match,pass,out,4,"
        f"0x0,,64,{tag},0,DF,6,tcp,50,{src},{dst},{40000 + tag},{dport},0,S,1,,65535,,mss;nop;wscale"
    )


def test_detect_beaconing_flags_regular_interval(monkeypatch):
    """Eventos muy regulares en el tiempo -> se detectan como posible beaconing."""
    from datetime import datetime, timedelta

    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        return {
            "severity": "high",
            "event_type": "posible C2",
            "explanation": "Conexiones salientes muy regulares hacia el mismo destino.",
            "recommended_action": "Aislar el host y analizar el proceso responsable.",
        }

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    base = datetime.utcnow()
    with Session(engine) as session:
        for i in range(6):
            event = NetworkEvent(
                source_ip="192.0.2.1",
                raw_message=_pass_out_message("192.168.10.15", "192.0.2.77", 443, i),
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            event.received_at = base + timedelta(seconds=30 * i)  # intervalo perfectamente regular
            session.add(event)
            session.commit()

    client = TestClient(app)
    resp = client.post("/events/detect-beaconing", params={"window_minutes": 60, "min_occurrences": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["groups_detected"] == 1
    assert data["groups"][0]["dst_ip"] == "192.0.2.77"
    assert data["groups"][0]["severity"] == "high"


def test_detect_beaconing_ignores_irregular_interval():
    """Eventos con intervalos muy irregulares (tráfico humano normal) -> no se marcan."""
    from datetime import datetime, timedelta

    base = datetime.utcnow()
    irregular_offsets = [0, 3, 47, 51, 120, 121]  # nada de regularidad
    with Session(engine) as session:
        for i, offset in enumerate(irregular_offsets):
            event = NetworkEvent(
                source_ip="192.0.2.1",
                raw_message=_pass_out_message("192.168.10.16", "192.0.2.88", 443, i),
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            event.received_at = base + timedelta(seconds=offset)
            session.add(event)
            session.commit()

    client = TestClient(app)
    resp = client.post("/events/detect-beaconing", params={"window_minutes": 60, "min_occurrences": 5})
    assert resp.status_code == 200
    assert resp.json()["groups_detected"] == 0


def test_extract_dns_query_unbound_and_dnsmasq():
    from app.dns_parsing import extract_dns_query

    unbound = "Oct  5 15:16:46 fw1 unbound[96103]: [96103:0] info: 192.168.1.100 daisy.ubuntu.com. A IN"
    dnsmasq = "Dec  3 08:51:27 dnsmasq[1068]: query[A] daisy.ubuntu.com from 192.0.2.5"

    r1 = extract_dns_query(unbound)
    assert r1 == {"client_ip": "192.168.1.100", "domain": "daisy.ubuntu.com", "qtype": "A"}

    r2 = extract_dns_query(dnsmasq)
    assert r2 == {"client_ip": "192.0.2.5", "domain": "daisy.ubuntu.com", "qtype": "A"}

    assert extract_dns_query("Aug 17 filterlog: 1,,,100,em0,match,block,in,4") is None


def test_looks_like_dga_flags_random_not_legit_domains():
    from app.dns_heuristics import looks_like_dga

    assert looks_like_dga("kj3h9fkj2h7glabc9wq.top") is True
    assert looks_like_dga("google.com") is False
    assert looks_like_dga("actualizacion-windows.com") is False


def _dns_dga_message(client_ip: str, domain: str, tag: int) -> str:
    return f"Aug 17 00:00:{tag:02d} pfsense-prod dnsmasq[1068]: query[A] {domain} from {client_ip}"


def test_detect_suspicious_dns_flags_multiple_dga_domains(monkeypatch):
    """Un mismo cliente consultando varios dominios de alta entropia -> se marca el grupo."""
    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        return {
            "severity": "high",
            "event_type": "posible DGA",
            "explanation": "Multiples dominios de alta entropia desde el mismo host.",
            "recommended_action": "Aislar el host y revisar procesos.",
        }

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    dga_domains = [
        "kj3h9fkj2h7glabc9wq.top", "9zxpq7fmvbn3hslk2ab.xyz",
        "a8k2j9h6g5f4d3s2a1z.info", "mm3n2b1v9c8x7z6a5s4.biz",
    ]
    with Session(engine) as session:
        for i, domain in enumerate(dga_domains):
            session.add(NetworkEvent(
                source_ip="192.168.10.22",
                raw_message=_dns_dga_message("192.168.10.22", domain, i),
            ))
        session.commit()

    client = TestClient(app)
    resp = client.post("/events/detect-suspicious-dns", params={"window_minutes": 30, "min_distinct_domains": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["groups_detected"] == 1
    assert data["groups"][0]["client_ip"] == "192.168.10.22"
    assert len(data["groups"][0]["distinct_domains"]) == 4


def test_detect_suspicious_dns_ignores_legit_domains():
    with Session(engine) as session:
        for i, domain in enumerate(["google.com", "microsoft.com", "github.com"]):
            session.add(NetworkEvent(
                source_ip="192.168.10.40",
                raw_message=_dns_dga_message("192.168.10.40", domain, i),
            ))
        session.commit()

    client = TestClient(app)
    resp = client.post("/events/detect-suspicious-dns", params={"window_minutes": 30, "min_distinct_domains": 3})
    assert resp.status_code == 200
    assert resp.json()["groups_detected"] == 0


def _post_ingest(client, content: str, source: str = "manual"):
    return client.post("/events/ingest", json={"content": content, "source": source})


def test_ingest_paste_creates_events():
    client = TestClient(app)
    resp = _post_ingest(client, "línea uno\nlínea dos\nlínea tres")
    assert resp.status_code == 200
    assert resp.json() == {"ingested": 3, "skipped_empty": 0}

    # Consulta directa a la DB: /events está paginado y otros tests dejan
    # eventos con received_at en el futuro (beaconing), que no deben
    # interferir con la verificación de la ingesta.
    from sqlmodel import select

    with Session(engine) as session:
        manual = session.exec(select(NetworkEvent).where(NetworkEvent.source_ip == "manual")).all()
    assert len(manual) == 3
    assert all(e.analyzed is False for e in manual)
    assert {e.raw_message for e in manual} == {"línea uno", "línea dos", "línea tres"}


def test_ingest_skips_blank_and_crlf():
    client = TestClient(app)
    resp = _post_ingest(client, "primera\r\n\r\nsegunda\n\n   \ntercera\r\n")
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 3
    # splitlines() no emite un elemento vacío tras el salto final: 6 líneas crudas - 3 reales
    assert resp.json()["skipped_empty"] == 3


def test_ingest_empty_content_rejected():
    client = TestClient(app)
    for content in ("", "   ", "\n\n\n"):
        resp = _post_ingest(client, content)
        assert resp.status_code == 422


def test_ingest_over_cap_rejected():
    client = TestClient(app)
    from app.main import MAX_INGEST_LINES

    resp = _post_ingest(client, "\n".join(f"log {i}" for i in range(MAX_INGEST_LINES + 1)))
    assert resp.status_code == 422


def test_ingested_events_can_be_correlated(monkeypatch):
    """La ingesta manual alimenta la correlación existente sin tocarla."""
    from app import main as main_module

    async def fake_explain_correlated_events(logs: str, count: int):
        return {
            "severity": "high",
            "event_type": "fuerza bruta SSH",
            "explanation": "Multiples intentos desde la misma IP en poco tiempo.",
            "recommended_action": "Bloquear la IP origen.",
        }

    monkeypatch.setattr(main_module, "explain_correlated_events", fake_explain_correlated_events)

    client = TestClient(app)
    lines = "\n".join(_raw_message_with_attacker_ip("203.0.113.77", i) for i in range(6))
    resp = _post_ingest(client, lines)
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 6

    resp = client.post("/events/correlate", params={"window_minutes": 10, "threshold": 5})
    assert resp.status_code == 200
    data = resp.json()
    # Otros tests dejan grupos previos en la DB compartida, así que solo
    # verificamos que el grupo de los eventos ingeridos exista y sea alto.
    assert data["groups_detected"] >= 1
    mine = [g for g in data["groups"] if g["attacker_ip"] == "203.0.113.77"]
    assert len(mine) == 1
    assert mine[0]["severity"] == "high"
