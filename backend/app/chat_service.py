"""
Cliente para chat interactivo con Ollama vía /api/chat (streaming).
Reutiliza la configuración de httpx de llm_service.py para no
duplicar timeouts ni manejo de errores.
"""

import json
import logging
import time

import httpx

from app.llm_service import LLMAnalysisError, _ollama_client_kwargs

logger = logging.getLogger("ai-noc.chat")

OLLAMA_HOST = None  # se resuelve en runtime desde llm_service
OLLAMA_MODEL = None


def _get_config():
    """Lee la config de Ollama desde llm_service (lazy import para no circular)."""
    import app.llm_service as svc
    return svc.OLLAMA_HOST, svc.OLLAMA_MODEL


async def chat_stream(messages: list[dict], *, keep_alive: str = "10m"):
    """
    Async generator que hace streaming de una conversación con Ollama
    vía /api/chat. Yieldea strings con el contenido de cada fragmento.

    Al final del stream loguea métricas de tiempos (misma estructura que
    llm_service._call_ollama).

    Lanza LLMAnalysisError si Ollama no responde o la conexión falla.
    """
    host, model = _get_config()

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": keep_alive,
        "options": {"temperature": 0.1},
    }

    t_start = time.perf_counter()

    async with httpx.AsyncClient(**_ollama_client_kwargs()) as client:
        try:
            async with client.stream(
                "POST",
                f"{host}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        break
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content

        except httpx.HTTPError as exc:
            logger.exception("Fallo al llamar a Ollama /api/chat")
            raise LLMAnalysisError(f"Ollama no respondió: {exc}") from exc

    elapsed = time.perf_counter() - t_start
    logger.info("Chat streaming completado en %.2fs", elapsed)
