"""
Modelos de datos para AI-NOC Copilot.

Un NetworkEvent representa una línea de log normalizada, típicamente
proveniente del syslog de pfSense (bloqueos de firewall, caídas de VPN,
intentos de conexión, etc.).
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class NetworkEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    received_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_ip: str | None = Field(default=None, index=True)
    raw_message: str
    # Campos rellenados por el análisis con IA (inicialmente vacíos):
    severity: str | None = Field(default=None, index=True)  # low / medium / high
    event_type: str | None = Field(default=None)
    ai_explanation: str | None = Field(default=None)
    analyzed: bool = Field(default=False, index=True)
    correlation_group: int | None = Field(default=None, index=True)


class LLMTiming(SQLModel, table=True):
    """Registro de métricas de cada llamada a la API de Ollama /api/generate.

    Se escribe desde _call_ollama() en llm_service.py y se consulta desde
    el endpoint GET /performance/history y el dashboard de rendimiento.
    """

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    total_seconds: float = 0.0
    load_seconds: float = 0.0
    prompt_eval_seconds: float = 0.0
    prompt_eval_tokens: int = 0
    gen_seconds: float = 0.0
    gen_tokens: int = 0
    tokens_per_second: float = 0.0
    model: str = ""
    mode: str = ""  # "explain_event" o "explain_correlated"
