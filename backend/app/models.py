"""
Modelos de datos para AI-NOC Copilot.

Un NetworkEvent representa una línea de log normalizada, típicamente
proveniente del syslog de pfSense (bloqueos de firewall, caídas de VPN,
intentos de conexión, etc.).
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class NetworkEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    received_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_ip: Optional[str] = Field(default=None, index=True)
    raw_message: str
    # Campos rellenados por el análisis con IA (inicialmente vacíos):
    severity: Optional[str] = Field(default=None, index=True)  # low / medium / high
    event_type: Optional[str] = Field(default=None)
    ai_explanation: Optional[str] = Field(default=None)
    analyzed: bool = Field(default=False, index=True)
