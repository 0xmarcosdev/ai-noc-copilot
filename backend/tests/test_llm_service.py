"""
Tests unitarios para llm_service.py -- no necesita Ollama real, httpx se mockea.
"""
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.llm_service import _call_ollama


def _fake_ollama_response(
    text='{"severity":"high","event_type":"test","explanation":"x","recommended_action":"y"}',
    total_duration_ns=5_000_000_000,
    load_duration_ns=500_000_000,
    prompt_eval_count=50,
    prompt_eval_duration_ns=1_000_000_000,
    eval_count=100,
    eval_duration_ns=2_000_000_000,
):
    return {
        "response": text,
        "total_duration": total_duration_ns,
        "load_duration": load_duration_ns,
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_duration": prompt_eval_duration_ns,
        "eval_count": eval_count,
        "eval_duration": eval_duration_ns,
    }


def _make_mock_client(response_data):
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    return mock_client


@pytest.mark.asyncio
async def test_call_ollama_incluye_keep_alive_y_num_predict():
    """El payload enviado a Ollama debe incluir keep_alive y options.num_predict."""
    response_data = _fake_ollama_response()
    mock_client = _make_mock_client(response_data)

    with patch("app.llm_service.httpx.AsyncClient", return_value=mock_client):
        await _call_ollama("test prompt", keep_alive="15m", num_predict=300)

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

    assert payload is not None, "No se encontro payload en la llamada a post"
    assert payload["keep_alive"] == "15m"
    assert payload["options"]["num_predict"] == 300
    assert payload["options"]["temperature"] == 0.1
    assert payload["format"] == "json"
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_call_ollama_loguea_metadata_de_tiempos(caplog):
    """Se debe loguear 'tok/s' en la linea de timing."""
    response_data = _fake_ollama_response(
        eval_count=100,
        eval_duration_ns=2_000_000_000,
    )
    mock_client = _make_mock_client(response_data)

    with (
        caplog.at_level(logging.INFO, logger="ai-noc.llm"),
        patch("app.llm_service.httpx.AsyncClient", return_value=mock_client),
    ):
        await _call_ollama("test prompt")

    tok_messages = [r.message for r in caplog.records if "tok/s" in r.message]
    assert len(tok_messages) >= 1, (
        f"No se encontro 'tok/s' en los logs. "
        f"Mensajes capturados: {[r.message for r in caplog.records]}"
    )
