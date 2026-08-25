"""
Diagnóstico de latencia del LLM: 4 llamadas controladas a explain_event()
con el mismo log, midiendo tiempos de carga, prompt eval y generación.

Uso (desde la raíz del repo):
    cd backend
    ..\.venv\Scripts\python.exe -m scripts.diagnose_llm_latency
    O bien:
    ..\.venv\Scripts\python.exe ..\scripts\diagnose_llm_latency.py

Requiere Ollama corriendo en localhost:11434 con my-qwen-3b:latest.
NO requiere el backend FastAPI levantado (solo importa llm_service).
"""
import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

# Agregar backend/ al path para importar app.llm_service
_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.llm_service import explain_event  # noqa: E402

LOG_MESSAGE = (
    "Aug 16 00:00:01 pfsense-prod filterlog: 1,,,1000000001,igb0,match,block,in,4,"
    "0x0,,64,1000,0,DF,6,tcp,50,203.0.113.77,192.168.10.5,40001,22,0,S,1,,65535,,mss"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("diagnose_llm")


def _run(cmd: str) -> str:
    """Ejecuta un comando PowerShell y retorna stdout stripped."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def _ollama_stop():
    """Detiene el modelo forzando descarga de memoria."""
    logger.info(">>> ollama stop my-qwen-3b ...")
    out = _run("ollama stop my-qwen-3b")
    logger.info("    %s", out or "(sin salida)")


def _ollama_ps() -> str:
    """ Retorna el output de 'ollama ps'."""
    return _run("ollama ps")


async def _timed_call(call_num: int) -> dict:
    """
    Ejecuta explain_event() y retorna dict con métricas parseadas del
    log de Ollama. El logger de app.llm ya imprime la línea
    estructurada; este helper extrae los números para el reporte.
    """
    logger.info("=== Llamada %d ===", call_num)
    t0 = time.perf_counter()
    result = await explain_event(LOG_MESSAGE)
    elapsed = time.perf_counter() - t0
    logger.info("  Wall-clock total: %.2fs", elapsed)
    return {"call_num": call_num, "wall_clock": elapsed, "result": result}


async def main():
    logger.info("Diagnóstico de latencia LLM — modelo: my-qwen-3b:latest")
    logger.info("Log de prueba (%d chars): %s...", len(LOG_MESSAGE), LOG_MESSAGE[:80])
    logger.info("")

    # --- Llamada 1: cold start (forzar descarga previa) ---
    _ollama_stop()
    time.sleep(2)
    r1 = await _timed_call(1)

    # --- Llamada 2: hot (modelo ya cargado) ---
    r2 = await _timed_call(2)

    # --- Llamada 3: esperar 6 minutos ---
    logger.info("")
    logger.info("Esperando 6 minutos para verificar keep_alive=10m ...")
    logger.info("(El modelo NO debe descargarse si keep_alive funciona)")
    for remaining in range(360, 0, -1):
        mins, secs = divmod(remaining, 60)
        print(f"\r  Esperando: {mins:02d}:{secs:02d} restante", end="", flush=True)
        time.sleep(1)
    print()
    logger.info("")
    r3 = await _timed_call(3)

    # --- Llamada 4: con ollama ps en paralelo ---
    logger.info("Ejecutando 'ollama ps' en paralelo...")
    ps_output = _ollama_ps()
    r4 = await _timed_call(4)

    # --- Reporte consolidado ---
    logger.info("")
    logger.info("=" * 70)
    logger.info("REPORTE DE LATENCIA")
    logger.info("=" * 70)
    for r in (r1, r2, r3, r4):
        logger.info(
            "  Llamada %d: wall_clock=%.2fs",
            r["call_num"],
            r["wall_clock"],
        )
    logger.info("")
    logger.info("Output de 'ollama ps' (llamada 4):")
    logger.info(ps_output if ps_output else "  (sin salida)")
    logger.info("")

    # --- Plan de energía ---
    logger.info("Plan de energía activo:")
    logger.info(_run("powercfg /getactivescheme"))
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
