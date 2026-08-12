"""
Cliente delgado sobre la API de Ollama (compatible con /api/generate).
Mantiene toda la lógica de "cómo le hablo al LLM" en un solo lugar para
que cambiar de modelo (o de motor de inferencia) sea un cambio de una
línea, no una refactorización.
"""
import json
import os
from pathlib import Path

import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "my-qwen-3b:latest")

PROMPT_PATH = Path(__file__).parent / "prompts" / "threat_explainer.txt"
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


class LLMAnalysisError(Exception):
    pass


async def explain_event(log_raw: str) -> dict:
    """
    Envía un evento de log al modelo local y devuelve un dict con
    severity / event_type / explanation / recommended_action.
    Lanza LLMAnalysisError si Ollama no responde o el JSON es inválido,
    para que el endpoint decida cómo degradar (ver main.py).
    """
    prompt = PROMPT_TEMPLATE.format(log_raw=log_raw)

    async with httpx.AsyncClient(timeout=60.0) as client:
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
            raise LLMAnalysisError(f"Ollama no respondió: {exc}") from exc

    raw_text = response.json().get("response", "")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMAnalysisError(f"Respuesta no es JSON válido: {raw_text[:200]}") from exc

    for key in ("severity", "event_type", "explanation", "recommended_action"):
        parsed.setdefault(key, "desconocido")

    return parsed
