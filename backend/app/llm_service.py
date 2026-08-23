"""
Cliente delgado sobre la API de Ollama (compatible con /api/generate).
Mantiene toda la lógica de "cómo le hablo al LLM" en un solo lugar para
que cambiar de modelo (o de motor de inferencia) sea un cambio de una
línea, no una refactorización.
"""

import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("ai-noc.llm")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "my-qwen-3b:latest")

PROMPT_PATH = Path(__file__).parent / "prompts" / "threat_explainer.txt"
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


class LLMAnalysisError(Exception):
    pass


def _ollama_client_kwargs() -> dict:
    # Timeout con fases separadas + sin reutilizar conexiones keep-alive --
    # evita "Server disconnected without sending a response" (ver DEVLOG).
    return {
        "timeout": httpx.Timeout(120.0, connect=15.0),
        "limits": httpx.Limits(max_keepalive_connections=0, max_connections=5),
        "trust_env": False,
    }


async def explain_event(log_raw: str) -> dict:
    """
    Envía un evento de log al modelo local y devuelve un dict con
    severity / event_type / explanation / recommended_action.
    Lanza LLMAnalysisError si Ollama no responde o el JSON es inválido,
    para que el endpoint decida cómo degradar (ver main.py).
    """
    prompt = PROMPT_TEMPLATE.format(log_raw=log_raw)

    async with httpx.AsyncClient(**_ollama_client_kwargs()) as client:
        try:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Fallo al llamar a Ollama")
            raise LLMAnalysisError(f"Ollama no respondió: {exc}") from exc

    raw_text = response.json().get("response", "")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMAnalysisError(f"Respuesta no es JSON válido: {raw_text[:200]}") from exc

    for key in ("severity", "event_type", "explanation", "recommended_action"):
        parsed.setdefault(key, "desconocido")

    return parsed


CORRELATION_PROMPT_PATH = Path(__file__).parent / "prompts" / "correlation_explainer.txt"
CORRELATION_PROMPT_TEMPLATE = CORRELATION_PROMPT_PATH.read_text(encoding="utf-8")


async def explain_correlated_events(logs: str, count: int) -> dict:
    """
    Igual que explain_event(), pero recibe VARIOS logs relacionados en un
    solo prompt para que el modelo evalúe el patrón conjunto (ver
    SPEC.md §7 -- resuelve la limitación de análisis evento-por-evento).
    """
    prompt = CORRELATION_PROMPT_TEMPLATE.format(logs=logs, count=count)

    async with httpx.AsyncClient(**_ollama_client_kwargs()) as client:
        try:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Fallo al llamar a Ollama (correlación)")
            raise LLMAnalysisError(f"Ollama no respondió: {exc}") from exc

    raw_text = response.json().get("response", "")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMAnalysisError(f"Respuesta no es JSON válido: {raw_text[:200]}") from exc

    for key in ("severity", "event_type", "explanation", "recommended_action"):
        parsed.setdefault(key, "desconocido")

    return parsed
