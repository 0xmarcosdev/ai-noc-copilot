"""
Cliente delgado sobre la API de Ollama (compatible con /api/generate).
Toda la lógica de "cómo le hablo al LLM" vive aquí para que cambiar
de modelo (o de motor de inferencia) sea un cambio de una línea, no
una refactorización.
"""

import json
import logging
import os
from pathlib import Path

import httpx
from sqlmodel import Session, create_engine

from app.models import LLMTiming

logger = logging.getLogger("ai-noc.llm")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "my-qwen-3b:latest")

_DB_PATH = Path(os.getenv("DB_PATH", "./data/events.db")).resolve()
_llm_engine = create_engine(f"sqlite:///{_DB_PATH}", connect_args={"check_same_thread": False})

PROMPT_PATH = Path(__file__).parent / "prompts" / "threat_explainer.txt"
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

CORRELATION_PROMPT_PATH = Path(__file__).parent / "prompts" / "correlation_explainer.txt"
CORRELATION_PROMPT_TEMPLATE = CORRELATION_PROMPT_PATH.read_text(encoding="utf-8")


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


async def _call_ollama(
    prompt: str,
    *,
    keep_alive: str = "10m",
    num_predict: int = 400,
    mode: str = "explain_event",
) -> dict:
    """
    Helper compartido por todas las funciones públicas. Envía el prompt a
    Ollama, loguea métricas de tiempos siempre, y devuelve el dict con
    las 4 claves del contrato (severity/event_type/explanation/
    recommended_action).
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": keep_alive,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }

    async with httpx.AsyncClient(**_ollama_client_kwargs()) as client:
        try:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Fallo al llamar a Ollama")
            raise LLMAnalysisError(f"Ollama no respondió: {exc}") from exc

    result = response.json()

    # --- Logging estructurado de métricas (siempre, no solo en debug) ---
    total_ns = result.get("total_duration", 0)
    load_ns = result.get("load_duration", 0)
    prompt_eval_count = result.get("prompt_eval_count", 0)
    prompt_eval_ns = result.get("prompt_eval_duration", 0)
    eval_count = result.get("eval_count", 0)
    eval_ns = result.get("eval_duration", 0)

    total_s = total_ns / 1e9
    load_s = load_ns / 1e9
    prompt_eval_s = prompt_eval_ns / 1e9
    gen_s = eval_ns / 1e9
    tok_s = eval_count / gen_s if gen_s > 0 else 0.0

    logger.info(
        "Ollama timing: total=%.2fs load=%.2fs prompt_eval=%.2fs (%d tokens) "
        "gen=%.2fs (%d tokens, %.1f tok/s)",
        total_s,
        load_s,
        prompt_eval_s,
        prompt_eval_count,
        gen_s,
        eval_count,
        tok_s,
    )

    # --- Persistir métricas en SQLite ---
    try:
        with Session(_llm_engine) as session:
            session.add(
                LLMTiming(
                    total_seconds=total_s,
                    load_seconds=load_s,
                    prompt_eval_seconds=prompt_eval_s,
                    prompt_eval_tokens=prompt_eval_count,
                    gen_seconds=gen_s,
                    gen_tokens=eval_count,
                    tokens_per_second=tok_s,
                    model=OLLAMA_MODEL,
                    mode=mode,
                )
            )
            session.commit()
    except Exception:
        logger.warning("No se pudo persistir LLMTiming (BD no disponible)", exc_info=True)

    # --- Parseo de respuesta ---
    raw_text = result.get("response", "")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMAnalysisError(f"Respuesta no es JSON válido: {raw_text[:200]}") from exc

    for key in ("severity", "event_type", "explanation", "recommended_action"):
        parsed.setdefault(key, "desconocido")

    return parsed


async def explain_event(log_raw: str) -> dict:
    """
    Envía un evento de log al modelo local y devuelve un dict con
    severity / event_type / explanation / recommended_action.
    Lanza LLMAnalysisError si Ollama no responde o el JSON es inválido,
    para que el endpoint decida cómo degradar (ver main.py).
    """
    prompt = PROMPT_TEMPLATE.format(log_raw=log_raw)
    return await _call_ollama(prompt, mode="explain_event")


async def explain_correlated_events(logs: str, count: int) -> dict:
    """
    Igual que explain_event(), pero recibe VARIOS logs relacionados en un
    solo prompt para que el modelo evalúe el patrón conjunto (ver
    SPEC.md §7 -- resuelve la limitación de análisis evento-por-evento).
    """
    prompt = CORRELATION_PROMPT_TEMPLATE.format(logs=logs, count=count)
    return await _call_ollama(prompt, mode="explain_correlated")
