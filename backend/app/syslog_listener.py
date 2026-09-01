"""
Listener UDP de syslog. pfSense puede exportar sus logs directamente
a este puerto: Status > System Logs > Settings > "Remote Log Servers".

Corre como una tarea asíncrona en background dentro de FastAPI (ver main.py).
No hace parsing profundo del formato pfSense todavía -- eso es intencional:
para el MVP guardamos el mensaje crudo y dejamos que el LLM extraiga
severidad/tipo en analyze(). Un parser dedicado (regex por formato de
pfSense: filterlog, openvpn, etc.) es la primera mejora natural post-MVP.
"""
import asyncio
import logging
from datetime import datetime

from sqlmodel import Session

from app.models import NetworkEvent

logger = logging.getLogger("syslog_listener")


class SyslogProtocol(asyncio.DatagramProtocol):
    """Protocolo UDP para recibir logs de syslog y guardarlos en BD."""

    def __init__(self, engine):
        self.engine = engine

    def datagram_received(self, data: bytes, addr):
        message = data.decode(errors="replace").strip()
        source_ip = addr[0]
        logger.info("syslog from %s: %s", source_ip, message[:200])
        with Session(self.engine) as session:
            event = NetworkEvent(
                received_at=datetime.utcnow(),
                source_ip=source_ip,
                raw_message=message,
            )
            session.add(event)
            session.commit()


async def start_syslog_listener(engine, host: str, port: int):
    """Arranca el listener UDP de syslog en el host/puerto indicados.

    Args:
        engine: Motor SQLAlchemy para la BD.
        host: IP donde escuchar (ej. "0.0.0.0" para todas).
        port: Puerto UDP (por defecto 5514).

    Returns:
        Transporte asyncio para poder cerrarlo en shutdown.
    """
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: SyslogProtocol(engine),
        local_addr=(host, port),
    )
    logger.info("Syslog listener escuchando en %s:%s/udp", host, port)
    return transport