import logging
import os
import re
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal, Optional

from dotenv import load_dotenv

load_dotenv()  # carga backend/.env si existe -- evita usar export/set a mano en cada terminal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, BeforeValidator
from sqlalchemy import func
from sqlmodel import Session, SQLModel, create_engine, select

from app.chat_service import chat_stream
from app.dns_heuristics import looks_like_dga
from app.dns_parsing import extract_dns_query
from app.llm_service import LLMAnalysisError, explain_correlated_events, explain_event
from app.models import NetworkEvent
from app.syslog_listener import start_syslog_listener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-noc")

DB_PATH = Path(os.getenv("DB_PATH", "./data/events.db")).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # SQLite no crea la carpeta contenedora sola
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", "5514"))
CORRELATION_THRESHOLD = int(os.getenv("CORRELATION_THRESHOLD", "5"))
MAX_INGEST_LINES = int(os.getenv("MAX_INGEST_LINES", "5000"))

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


def extract_attacker_ip(raw_message: str) -> str | None:
    match = FILTERLOG_IPV4_RE.search(raw_message)
    return match.group("srcip") if match else None


# Extrae accion/direccion + IPs para el detector de beaconing
FILTERLOG_CONNECTION_RE = re.compile(
    r"filterlog:\s*\d+,,[^,]*,\d+,[^,]+,\w+,(?P<action>\w+),(?P<direction>\w+),4,"
    r"[^,]*,[^,]*,\d+,\d+,\d+,\w+,\d+,\w+,"
    r"\d+,(?P<srcip>[\d.]+),(?P<dstip>[\d.]+),"
    r"(?P<srcport>\d+),(?P<dstport>\d+)"
)


def extract_connection_summary(raw_message: str) -> dict | None:
    match = FILTERLOG_CONNECTION_RE.search(raw_message)
    return match.groupdict() if match else None


# Umbral mínimo de eventos con puerto extraído para animarse a clasificar el
# patrón -- con pocos eventos (ej. 2) cualquier mezcla de puertos es
# estadísticamente indeterminada, no un escaneo real. Ver Fase 4/§7 SPEC.
MIN_EVENTS_FOR_PORT_PATTERN = 3
# Fracción de puertos distintos sobre el total de eventos. Fuerza bruta =
# casi todos los eventos apuntan al MISMO puerto (ratio bajo, ej. 5 intentos
# SSH -> 1 puerto distinto de 5 = 0.2). Escaneo de puertos = casi todos los
# eventos apuntan a un puerto DISTINTO (ratio alto, ej. 6 puertos distintos
# de 6 eventos = 1.0). Zona intermedia => no nos animamos a clasificar.
BRUTEFORCE_MAX_RATIO = 0.3
PORTSCAN_MIN_RATIO = 0.7


def classify_port_pattern(events: list[NetworkEvent]) -> str | None:
    """Heurística determinista para distinguir fuerza bruta de escaneo de puertos.

    Fuerza bruta: muchos eventos, casi todos contra el MISMO puerto destino
    (ej. 10 intentos SSH al puerto 22 desde la misma IP).
    Escaneo de puertos: muchos eventos, cada uno contra un puerto destino
    DISTINTO (ej. recorrido secuencial de puertos).
    No decide nada por sí sola sobre severidad/malicia -- eso lo hace el LLM
    a partir de este hallazgo, nunca al revés (ver SPEC.md §"detección
    determinista").
    """
    dst_ports = []
    for event in events:
        conn = extract_connection_summary(event.raw_message)
        if conn:
            dst_ports.append(conn["dstport"])

    if len(dst_ports) < MIN_EVENTS_FOR_PORT_PATTERN:
        return None

    distinct_ratio = len(set(dst_ports)) / len(dst_ports)
    if distinct_ratio <= BRUTEFORCE_MAX_RATIO:
        return "fuerza_bruta"
    if distinct_ratio >= PORTSCAN_MIN_RATIO:
        return "escaneo_puertos"
    return None


def _parse_ingest_content(content: str) -> list[str]:
    """Divide el contenido pegado/subido en líneas de log, descartando vacías."""
    return [line.strip() for line in content.splitlines() if line.strip()]


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


@app.get("/performance/stats")
def performance_stats():
    """
    Devuelve estadísticas acumuladas y recientes de rendimiento de LLM (/api/generate)
    para el apartado de rendimiento y trade-offs del dashboard.
    """
    from app.models import LLMTiming
    from sqlmodel import select, func
    import os

    with Session(engine) as session:
        timings = session.exec(select(LLMTiming).order_by(LLMTiming.timestamp.desc()).limit(100)).all()
        total_calls = session.exec(select(func.count(LLMTiming.id))).one()

        avg_total = session.exec(select(func.avg(LLMTiming.total_seconds))).one() or 0.0
        avg_gen = session.exec(select(func.avg(LLMTiming.gen_seconds))).one() or 0.0
        avg_tps = session.exec(select(func.avg(LLMTiming.tokens_per_second))).one() or 0.0

        # Última llamada registrada
        latest = timings[0] if timings else None

        history = [
            {
                "id": t.id,
                "timestamp": t.timestamp.isoformat(),
                "total_seconds": t.total_seconds,
                "load_seconds": t.load_seconds,
                "prompt_eval_seconds": t.prompt_eval_seconds,
                "prompt_eval_tokens": t.prompt_eval_tokens,
                "gen_seconds": t.gen_seconds,
                "gen_tokens": t.gen_tokens,
                "tokens_per_second": t.tokens_per_second,
                "model": t.model,
                "mode": t.mode,
            }
            for t in reversed(timings)
        ]

    return {
        "hardware_info": {
            "gpu": "NVIDIA GeForce MX150 (2GB VRAM)",
            "architecture": "Pascal (384 CUDA cores)",
            "current_model": os.getenv("OLLAMA_MODEL", "my-qwen-3b:latest"),
            "vram_limit": "2.0 GB",
            "model_memory": "~2.4 GB (Modelo 3.4B Q4_K_M)",
            "offload_split": "74% CPU / 26% GPU (por restricción de VRAM)",
        },
        "summary": {
            "total_calls": total_calls,
            "avg_total_seconds": round(avg_total, 2),
            "avg_generation_seconds": round(avg_gen, 2),
            "avg_tokens_per_second": round(avg_tps, 2),
            "latest": latest.model_dump() if latest else None,
        },
        "history": history,
        "trade_offs": [
            {
                "option": "Modelo actual (Qwen 3.4B Q4_K_M)",
                "vram": "~2.4 GB",
                "speed": "~5.2 tok/s (~19s por respuesta)",
                "quality": "Alta (Razonamiento completo)",
                "recommended": False,
                "description": "Excede ligeramente los 2GB de la MX150. Se ejecuta parcialmente en CPU (74%), generando el cuello de botella físico.",
            },
            {
                "option": "Opción A: Qwen 2.5 1.5B (Q4_K_M)",
                "vram": "~1.1 GB",
                "speed": "~30-40 tok/s (~3-5s por respuesta)",
                "quality": "Muy buena para clasificación de logs",
                "recommended": True,
                "description": "Entra 100% en la VRAM de la MX150. Acelera la inferencia x4 sin perder precisión clave en seguridad perimetral.",
            },
            {
                "option": "Opción B: Cuantización Q3_K_M (3.4B)",
                "vram": "~1.7 GB",
                "speed": "~15s por respuesta",
                "quality": "Media-Alta",
                "recommended": False,
                "description": "Comprime el modelo 3B para que quepa en 2GB VRAM, pero introduce ligera pérdida de razonamiento.",
            },
            {
                "option": "Opción C: CPU Pura Q8_0 (3.4B)",
                "vram": "0 GB (Solo RAM)",
                "speed": "~5-7 tok/s (~18s por respuesta)",
                "quality": "Alta",
                "recommended": False,
                "description": "Evita la latencia de transferencia CPU<->GPU ejecutando todo en CPU. Mantiene velocidad similar pero libera VRAM.",
            },
        ],
    }


@app.get("/debug-ollama-config")
def debug_ollama():
    import os

    return {
        "OLLAMA_HOST": os.getenv("OLLAMA_HOST"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL"),
    }


def _empty_to_none(v):
    return None if v == "" else v


NormInt = Annotated[int | None, BeforeValidator(_empty_to_none)]
NormDatetime = Annotated[datetime | None, BeforeValidator(_empty_to_none)]


@app.get("/events")
def list_events(
    limit: int = 50,
    offset: int = 0,
    only_unanalyzed: bool = False,
    q: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    id_from: NormInt = None,
    id_to: NormInt = None,
    received_at_from: NormDatetime = None,
    received_at_to: NormDatetime = None,
    sort_by: Literal["id", "received_at", "severity", "event_type"] = "received_at",
    sort_dir: Literal["asc", "desc"] = "desc",
):
    """
    Lista eventos con paginación y filtros opcionales (FASE B).
    Respuesta: {total, limit, offset, items}.
    """
    limit = max(limit, 1)
    limit = min(limit, 500)
    offset = max(offset, 0)

    with Session(engine) as session:
        filters = []
        if only_unanalyzed:
            filters.append(NetworkEvent.analyzed == False)
        if severity:
            filters.append(NetworkEvent.severity == severity)
        if event_type:
            filters.append(NetworkEvent.event_type.contains(event_type))
        if q:
            filters.append(NetworkEvent.raw_message.contains(q))
        if id_from is not None:
            filters.append(NetworkEvent.id >= id_from)
        if id_to is not None:
            filters.append(NetworkEvent.id <= id_to)
        if received_at_from is not None:
            filters.append(NetworkEvent.received_at >= received_at_from)
        if received_at_to is not None:
            filters.append(NetworkEvent.received_at <= received_at_to)

        count_stmt = select(func.count()).select_from(NetworkEvent)
        for f in filters:
            count_stmt = count_stmt.where(f)
        total = session.exec(count_stmt).one()

        sort_column = getattr(NetworkEvent, sort_by)
        # Desempate por ID para paginación determinista (SPEC §5)
        tiebreaker = NetworkEvent.id.desc() if sort_dir == "desc" else NetworkEvent.id.asc()
        query = select(NetworkEvent)
        for f in filters:
            query = query.where(f)
        query = (
            query.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc(), tiebreaker)
            .offset(offset)
            .limit(limit)
        )
        items = session.exec(query).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }


@app.get("/events/correlation-history")
def correlation_history(limit: Optional[int] = 50):
    """Historial de grupos de correlación agrupados por correlation_group."""
    # Si por alguna razón llega None, usamos 50
    actual_limit = limit if limit is not None else 50

    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent)
            .where(NetworkEvent.correlation_group.is_not(None))
            .order_by(NetworkEvent.correlation_group.desc(), NetworkEvent.received_at)
        ).all()

    groups: dict[int, list[NetworkEvent]] = defaultdict(list)
    for e in events:
        groups[e.correlation_group].append(e)

    result = []
    for gid in sorted(groups, reverse=True):
        gevents = groups[gid]
        attacker_ips = set()
        ports = set()
        for e in gevents:
            ip = extract_attacker_ip(e.raw_message)
            if ip:
                attacker_ips.add(ip)
            conn = extract_connection_summary(e.raw_message)
            if conn:
                ports.add(conn["dstport"])
        result.append(
            {
                "correlation_group": gid,
                "event_count": len(gevents),
                "attacker_ips": sorted(attacker_ips),
                "unique_ports": sorted(ports),
                "pattern": classify_port_pattern(gevents),
                "severity": gevents[0].severity,
                "first_seen": min(e.received_at for e in gevents).isoformat(),
                "last_seen": max(e.received_at for e in gevents).isoformat(),
                "event_ids": [e.id for e in gevents],
            }
        )
    return {"total_groups": len(result), "groups": result[:actual_limit]}


@app.get("/events/{event_id}")
def get_event(event_id: int):
    with Session(engine) as session:
        event = session.get(NetworkEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Evento no encontrado")
        return event


class IngestRequest(BaseModel):
    content: str
    source: str = "manual"


@app.post("/events/ingest")
def ingest_events(req: IngestRequest):
    lines = _parse_ingest_content(req.content)
    if not lines:
        raise HTTPException(status_code=422, detail="No se encontraron líneas de log en el contenido")
    if len(lines) > MAX_INGEST_LINES:
        raise HTTPException(
            status_code=422,
            detail=f"Demasiadas líneas ({len(lines)}); máximo permitido: {MAX_INGEST_LINES}",
        )

    with Session(engine) as session:
        session.add_all(
            NetworkEvent(received_at=datetime.utcnow(), source_ip=req.source, raw_message=line)
            for line in lines
        )
        session.commit()

    return {"ingested": len(lines), "skipped_empty": len(req.content.splitlines()) - len(lines)}


@app.post("/events/{event_id}/analyze")
async def analyze_event(event_id: int):
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


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/events/{event_id}/chat")
async def chat_with_event(event_id: int, req: ChatRequest):
    """Chat interactivo sobre un evento específico. Streaming puro: cada
    fragmento de la respuesta del LLM se yieldea a medida que Ollama lo
    genera (ver chat_service.py). No hay estado en el backend -- el
    frontend manda el historial completo en cada llamada."""
    with Session(engine) as session:
        event = session.get(NetworkEvent, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Evento no encontrado")

        # Armar system message con contexto real del evento
        system_parts = [
            (
                "Eres un analista de seguridad de redes (copiloto NOC local). "
                "Responde en español, de forma directa y técnica. "
                "NUNCA inventes IPs, puertos, o contexto de red que no esté en los datos reales."
            ),
            f"Evento de log crudo:\n{event.raw_message}",
        ]

        if event.analyzed:
            system_parts.append(
                f"Análisis previo del evento: severidad={event.severity}, "
                f"tipo={event.event_type}.\n"
                f"Explicación del analista: {event.ai_explanation}"
            )

        if event.correlation_group is not None:
            # Buscar info del grupo de correlación
            group_events = session.exec(
                select(NetworkEvent).where(NetworkEvent.correlation_group == event.correlation_group)
            ).all()
            port_pattern = classify_port_pattern(group_events)
            system_parts.append(
                f"Este evento pertenece al grupo de correlación #{event.correlation_group} "
                f"con {len(group_events)} eventos relacionados. "
                f"Patrón clasificado: {port_pattern or 'indeterminado'}."
            )

        system_message = "\n\n".join(system_parts)
        messages = (
            [{"role": "system", "content": system_message}]
            + req.history
            + [{"role": "user", "content": req.message}]
        )

    # Validar que Ollama responde ANTES de enviar el status 200.
    # StreamingResponse compromete el status code inmediatamente; si el
    # generador falla después, el cliente recibe un stream truncado sin
    # código de error. Pequeña latencia extra en el primer chunk vale
    # el trade-off de poder devolver502 limpio.
    generator = chat_stream(messages)
    first_chunk = None
    try:
        first_chunk = await generator.__anext__()
    except LLMAnalysisError as exc:
        logger.error("Chat fallo antes de iniciar stream: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    async def _chain(first: str, rest):
        yield first
        async for chunk in rest:
            yield chunk

    return StreamingResponse(
        _chain(first_chunk, generator),
        media_type="text/plain",
    )


@app.post("/events/correlate")
async def correlate_events(window_minutes: int = 10, threshold: int = CORRELATION_THRESHOLD):
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent)
            .where(NetworkEvent.analyzed == False)
            .where(NetworkEvent.received_at >= cutoff)
        ).all()

        groups: dict[str, list[NetworkEvent]] = defaultdict(list)
        for event in events:
            attacker_ip = extract_attacker_ip(event.raw_message)
            if attacker_ip:
                # 1. Extraemos los campos de la conexión utilizando la función existente
                conn = extract_connection_summary(event.raw_message)

                # 2. Filtramos estrictamente: solo agrupamos si se pudo extraer la conexión
                #    y su acción es explícitamente "block"
                if conn and conn.get("action") == "block":
                    groups[attacker_ip].append(event)

        # correlation_group es un contador global creciente: nunca se
        # reutiliza un id, aunque haya huecos, para que el historial
        # (/events/correlation-history) no mezcle corridas distintas.
        max_group = session.exec(select(func.max(NetworkEvent.correlation_group))).one()
        next_group_id = (max_group or 0) + 1

    results = []
    for attacker_ip, group_events in groups.items():
        if len(group_events) < threshold:
            continue

        port_pattern = classify_port_pattern(group_events)
        combined_log = "\n".join(e.raw_message for e in group_events)
        context = (
            f"Patrón detectado por heurística de puertos destino: {len(group_events)} eventos "
            f"bloqueados desde el origen {attacker_ip}. Clasificación determinista según la "
            f"variedad de puertos: '{port_pattern or 'indeterminado'}' (fuerza_bruta = mismo "
            f"puerto repetido, escaneo_puertos = puertos distintos en cada intento).\n\n"
            f"Eventos:\n{combined_log}"
        )
        try:
            result = await explain_correlated_events(context, count=len(group_events))
        except LLMAnalysisError as exc:
            logger.error("Fallo al correlacionar grupo %s: %s", attacker_ip, exc)
            continue

        group_id = next_group_id
        next_group_id += 1

        event_ids = [e.id for e in group_events]
        with Session(engine) as session:
            for event_id in event_ids:
                db_event = session.get(NetworkEvent, event_id)
                db_event.severity = result["severity"]
                db_event.event_type = f"patrón correlacionado: {result['event_type']}"
                db_event.ai_explanation = result["explanation"]
                db_event.analyzed = True
                db_event.correlation_group = group_id
                session.add(db_event)
            session.commit()

        results.append(
            {
                "attacker_ip": attacker_ip,
                "event_count": len(group_events),
                "event_ids": event_ids,
                "correlation_group": group_id,
                "port_pattern": port_pattern,
                **result,
            }
        )

    return {
        "window_minutes": window_minutes,
        "threshold": threshold,
        "groups_detected": len(results),
        "groups": results,
    }


@app.post("/events/detect-beaconing")
async def detect_beaconing(window_minutes: int = 60, min_occurrences: int = 5, max_cv: float = 0.15):
    """
    Detecta posible "malware phoning home" (beaconing C2): conexiones
    salientes PERMITIDAS (pass, out) repetidas hacia el mismo destino con
    intervalos de tiempo muy regulares -- patrón típico de malware que
    llama a su servidor de control cada N segundos/minutos, distinto del
    tráfico humano normal (irregular). La detección es determinista
    (coeficiente de variación del intervalo entre eventos); el LLM solo
    redacta la explicación sobre el hallazgo -- ver SPEC.md.

    max_cv: coeficiente de variación (desviación estándar / media) máximo
    para considerar el patrón "sospechosamente regular". Valores bajos
    (ej. 0.15 = 15%) son más estrictos; tráfico humano normal suele tener
    CV mucho más alto (>0.5).
    """
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent)
            .where(NetworkEvent.analyzed == False)
            .where(NetworkEvent.received_at >= cutoff)
        ).all()

        groups: dict[tuple, list[NetworkEvent]] = defaultdict(list)
        for event in events:
            conn = extract_connection_summary(event.raw_message)
            if conn and conn["action"] == "pass" and conn["direction"] == "out":
                key = (conn["srcip"], conn["dstip"], conn["dstport"])
                groups[key].append(event)

    results = []
    for (src, dst, dport), group_events in groups.items():
        if len(group_events) < min_occurrences:
            continue

        timestamps = sorted(e.received_at for e in group_events)
        intervals = [(timestamps[i + 1] - timestamps[i]).total_seconds() for i in range(len(timestamps) - 1)]
        if not intervals or any(i <= 0 for i in intervals):
            continue

        mean_interval = sum(intervals) / len(intervals)
        variance = sum((i - mean_interval) ** 2 for i in intervals) / len(intervals)
        stddev = variance**0.5
        cv = stddev / mean_interval if mean_interval > 0 else 999

        if cv > max_cv:
            continue  # muy irregular -- probablemente tráfico humano normal, no beaconing

        combined_log = "\n".join(e.raw_message for e in group_events)
        context = (
            f"Patrón detectado por heurística: {len(group_events)} conexiones salientes "
            f"PERMITIDAS de {src} hacia {dst}:{dport}, con intervalo promedio de "
            f"{mean_interval:.1f} segundos y una variacion de solo {cv * 100:.1f}% "
            f"(muy regular -- tipico de un proceso automatizado llamando a un servidor "
            f"remoto a intervalos fijos, no de uso humano normal).\n\nEventos:\n{combined_log}"
        )
        try:
            result = await explain_correlated_events(context, count=len(group_events))
        except LLMAnalysisError as exc:
            logger.error("Fallo al analizar beaconing %s->%s:%s: %s", src, dst, dport, exc)
            continue

        event_ids = [e.id for e in group_events]
        with Session(engine) as session:
            for event_id in event_ids:
                db_event = session.get(NetworkEvent, event_id)
                db_event.severity = result["severity"]
                db_event.event_type = f"posible beaconing: {result['event_type']}"
                db_event.ai_explanation = result["explanation"]
                db_event.analyzed = True
                session.add(db_event)
            session.commit()

        results.append(
            {
                "src_ip": src,
                "dst_ip": dst,
                "dst_port": dport,
                "event_count": len(group_events),
                "mean_interval_seconds": round(mean_interval, 1),
                "coefficient_of_variation": round(cv, 3),
                "event_ids": event_ids,
                **result,
            }
        )

    return {"window_minutes": window_minutes, "groups_detected": len(results), "groups": results}


@app.post("/events/detect-suspicious-dns")
async def detect_suspicious_dns(window_minutes: int = 30, min_distinct_domains: int = 3):
    """
    Detecta posible malware con generación algorítmica de dominios (DGA)
    o exfiltración vía DNS: un mismo host consultando VARIOS dominios de
    alta entropía distintos en poco tiempo -- patrón típico de malware
    "probando" dominios de C2 hasta encontrar uno activo. La detección de
    "¿es este dominio sospechoso?" es determinista (dns_heuristics.py,
    entropía de Shannon) -- el LLM nunca decide eso, solo redacta la
    explicación sobre lo que la heurística ya marcó. Ver SPEC.md.

    Requiere que pfSense tenga habilitado el logging de consultas DNS
    (Unbound o dnsmasq) apuntando al mismo listener de syslog.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    with Session(engine) as session:
        events = session.exec(
            select(NetworkEvent)
            .where(NetworkEvent.analyzed == False)
            .where(NetworkEvent.received_at >= cutoff)
        ).all()

        groups: dict[str, list[tuple[NetworkEvent, str]]] = defaultdict(list)
        for event in events:
            dns = extract_dns_query(event.raw_message)
            if dns and looks_like_dga(dns["domain"]):
                groups[dns["client_ip"]].append((event, dns["domain"]))

    results = []
    for client_ip, hits in groups.items():
        distinct_domains = sorted({domain for _, domain in hits})
        if len(distinct_domains) < min_distinct_domains:
            continue

        group_events = [e for e, _ in hits]
        domains_list = "\n".join(distinct_domains)
        context = (
            f"Patrón detectado por heurística de entropía: el host {client_ip} "
            f"consultó {len(distinct_domains)} dominios distintos con nombres de "
            f"alta entropía (aspecto pseudoaleatorio) en los últimos {window_minutes} "
            f"minutos -- comportamiento típico de malware con generación "
            f"algorítmica de dominios (DGA) probando servidores de C2, no de "
            f"navegación humana normal.\n\nDominios detectados:\n{domains_list}"
        )
        try:
            result = await explain_correlated_events(context, count=len(distinct_domains))
        except LLMAnalysisError as exc:
            logger.error("Fallo al analizar DNS sospechoso para %s: %s", client_ip, exc)
            continue

        event_ids = [e.id for e in group_events]
        with Session(engine) as session:
            for event_id in event_ids:
                db_event = session.get(NetworkEvent, event_id)
                db_event.severity = result["severity"]
                db_event.event_type = f"DNS sospechoso: {result['event_type']}"
                db_event.ai_explanation = result["explanation"]
                db_event.analyzed = True
                session.add(db_event)
            session.commit()

        results.append(
            {
                "client_ip": client_ip,
                "distinct_domains": distinct_domains,
                "event_count": len(group_events),
                "event_ids": event_ids,
                **result,
            }
        )

    return {"window_minutes": window_minutes, "groups_detected": len(results), "groups": results}


@app.get("/summary")
def summary(hours: int = 24):
    """Resumen enriquecido para el dashboard: distribución por severidad,
    tipos dominantes, series temporales, correlación y exportación.
    """
    with Session(engine) as session:
        events = session.exec(select(NetworkEvent).where(NetworkEvent.analyzed == True)).all()

        by_severity: dict[str, int] = {}
        high_severity_types: dict[str, int] = {}
        by_type: dict[str, int] = {}
        correlated_count = 0

        for e in events:
            sev = e.severity or "low"
            by_severity[sev] = by_severity.get(sev, 0) + 1
            if sev == "high" and e.event_type:
                high_severity_types[e.event_type] = high_severity_types.get(e.event_type, 0) + 1
            etype = e.event_type or "sin clasificar"
            by_type[etype] = by_type.get(etype, 0) + 1
            if e.correlation_group is not None:
                correlated_count += 1

        top_high_categories = sorted(high_severity_types.items(), key=lambda kv: kv[1], reverse=True)[:3]

        # Serie temporal: eventos por hora de los últimos `hours`
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        hourly_counts: dict[str, int] = {}
        for e in events:
            if e.received_at >= cutoff:
                bucket = e.received_at.strftime("%Y-%m-%d %H:00")
                hourly_counts[bucket] = hourly_counts.get(bucket, 0) + 1

        time_series = [{"hour": h, "count": hourly_counts[h]} for h in sorted(hourly_counts)]

        return {
            "total_analyzed": len(events),
            "by_severity": by_severity,
            "top_high_severity_types": [{"event_type": t, "count": c} for t, c in top_high_categories],
            "by_event_type": [
                {"event_type": t, "count": c}
                for t, c in sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)
            ],
            "correlated_count": correlated_count,
            "individual_count": len(events) - correlated_count,
            "time_series": time_series,
        }
