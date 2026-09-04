#!/usr/bin/env python3
"""
TUI simple para el generador de logs sintéticos de AI-NOC Copilot.

Orquesta `scripts/generate_fake_logs.py` sin duplicar su lógica.
Reutiliza build_message, SCENARIOS, build_tcp_line, etc. importándolos.

Uso:
    python scripts/fake_logs_tui.py

Dependencias opcionales (con fallback a stdlib):
    rich         -> menús bonitos y colores
    pyperclip    -> copiar al portapapeles en Windows
"""

import sys
import os
import time
import random
from datetime import datetime
from pathlib import Path

# Añadir el directorio scripts al path para importar el generador
SCRIPTS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from generate_fake_logs import (
        SCENARIOS,
        build_message,
        scenario_portscan,
        COMMON_PORTS,
    )
except ImportError as e:
    print(f"Error importando generate_fake_logs: {e}")
    sys.exit(1)

# --- Dependencias opcionales con fallback ---
try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, IntPrompt
    from rich.panel import Panel
    from rich import print as rprint
    HAS_RICH = True
    console = Console()
    # Rich usa IntPrompt.ask para enteros
    ask_int = IntPrompt.ask
except ImportError:
    HAS_RICH = False
    console = None

    class _Prompt:
        @staticmethod
        def ask(prompt, default=None, choices=None):
            if choices:
                prompt = f"{prompt} [{'/'.join(choices)}]"
            if default is not None:
                prompt = f"{prompt} (default: {default})"
            val = input(f"{prompt}: ").strip()
            return val if val else default

        @staticmethod
        def ask_int(prompt, default=None):
            while True:
                val = _Prompt.ask(prompt, default=default)
                try:
                    return int(val)
                except ValueError:
                    print("Ingresa un numero entero valido.")

    Prompt = _Prompt()
    IntPrompt = _Prompt()
    ask_int = _Prompt.ask_int

    def rprint(*args, **kwargs):
        print(*args, **kwargs)

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False


# --- Configuración ---
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5514
DEFAULT_COUNT = 10
DEFAULT_INTERVAL = 0.5
OUT_DIR = SCRIPTS_DIR / "out"


ESCENARIOS_ORDEN = [
    "normal",
    "bruteforce",
    "portscan",
    "beacon",
    "dns_dga",
    "dns_normal",
    "vpn_flapping",
]

ESCENARIOS_DESC = {
    "normal": "Tráfico mixto normal (pass/block, TCP/UDP, VPN)",
    "bruteforce": "Fuerza bruta SSH (mismo puerto 22, IP atacante fija)",
    "portscan": "Escaneo de puertos (puertos distintos, IP atacante fija)",
    "beacon": "Beaconing C2 (conexiones salientes pass/out regulares)",
    "dns_dga": "DNS malicioso (dominios DGA alta entropía)",
    "dns_normal": "DNS normal (dominios legítimos)",
    "vpn_flapping": "VPN inestabilidad (timeouts openvpn)",
}


def print_header(titulo: str):
    if HAS_RICH:
        console.rule(f"[bold cyan]{titulo}[/bold cyan]")
    else:
        print(f"\n{'='*60}")
        print(f"  {titulo}")
        print(f"{'='*60}")


def print_info(msg: str):
    if HAS_RICH:
        console.print(f"[green][i][/green] {msg}")
    else:
        print(f"[INFO] {msg}")


def print_warn(msg: str):
    if HAS_RICH:
        console.print(f"[yellow][!][/yellow] {msg}")
    else:
        print(f"[AVISO] {msg}")


def print_error(msg: str):
    if HAS_RICH:
        console.print(f"[red][x][/red] {msg}")
    else:
        print(f"[ERROR] {msg}")


def print_success(msg: str):
    if HAS_RICH:
        console.print(f"[green][ok][/green] {msg}")
    else:
        print(f"[OK] {msg}")


def menu_escenario() -> str | None:
    """Muestra menú numerado de escenarios. Devuelve el nombre o None si sale."""
    while True:
        print_header("SELECCIONAR ESCENARIO")
        if HAS_RICH:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Nº", style="cyan", width=4)
            table.add_column("Escenario", style="white")
            table.add_column("Descripción", style="dim")
            for idx, esc in enumerate(ESCENARIOS_ORDEN, 1):
                table.add_row(str(idx), esc, ESCENARIOS_DESC[esc])
            table.add_row("0", "salir", "Volver al menú anterior / salir")
            console.print(table)
        else:
            for idx, esc in enumerate(ESCENARIOS_ORDEN, 1):
                print(f"  {idx}. {esc:15} - {ESCENARIOS_DESC[esc]}")
            print("  0. salir")

        try:
            choice = ask_int("\nElige un numero", default=1)
        except (EOFError, KeyboardInterrupt):
            return None

        if choice == 0:
            return None
        if 1 <= choice <= len(ESCENARIOS_ORDEN):
            return ESCENARIOS_ORDEN[choice - 1]

        print_error("Número inválido. Intenta de nuevo.")


def ask_count(default: int = DEFAULT_COUNT) -> int:
    """Pide cantidad de eventos (>0). Enter = default."""
    while True:
        try:
            val = Prompt.ask(
                f"\nCantidad de eventos del lote (Enter = {default})",
                default=str(default)
            )
            count = int(val)
            if count > 0:
                return count
            print_error("Debe ser un número mayor que 0.")
        except ValueError:
            print_error("Ingresa un número entero válido.")
        except (EOFError, KeyboardInterrupt):
            return default


def ask_interval(default: float = DEFAULT_INTERVAL, scenario: str = "") -> float:
    """Pide intervalo entre eventos en segundos."""
    # Para beacon, sugerir intervalo estable
    hint = ""
    if scenario == "beacon":
        hint = " (para beacon se recomienda intervalo fijo, ej. 30)"
    while True:
        try:
            val = Prompt.ask(
                f"Intervalo entre eventos en segundos (Enter = {default}){hint}",
                default=str(default)
            )
            interval = float(val)
            if interval >= 0:
                return interval
            print_error("Debe ser >= 0.")
        except ValueError:
            print_error("Ingresa un número válido (ej. 0.5, 1, 30).")
        except (EOFError, KeyboardInterrupt):
            return default


def menu_accion() -> int:
    """Menú de acción. Devuelve 1,2,3,4 o 0 para volver."""
    while True:
        print_header("ACCIONES DISPONIBLES")
        if HAS_RICH:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Nº", style="cyan", width=4)
            table.add_column("Acción", style="white")
            table.add_column("Detalle", style="dim")
            table.add_row("1", "Enviar al AI-NOC", "Genera lote y envía UDP a 127.0.0.1:5514")
            table.add_row("2", "Mostrar comando CLI", "Imprime comando python equivalente para copiar/pegar")
            table.add_row("3", "Copiar logs al portapapeles", "Genera líneas sin enviar; copia al clipboard")
            table.add_row("4", "Guardar logs en archivo", "Genera y guarda en scripts/out/fake_logs_<escenario>_<ts>.txt")
            table.add_row("0", "Volver", "Regresar al menú de escenarios")
            console.print(table)
        else:
            print("  1. Enviar al AI-NOC          - Genera lote y envía UDP a 127.0.0.1:5514")
            print("  2. Mostrar comando CLI       - Imprime comando python equivalente")
            print("  3. Copiar logs al portapapeles - Genera sin enviar; copia al clipboard")
            print("  4. Guardar logs en archivo     - Guarda en scripts/out/fake_logs_<escenario>_<ts>.txt")
            print("  0. Volver")

        try:
            choice = ask_int("\nElige una accion", default=1)
        except (EOFError, KeyboardInterrupt):
            return 0

        if 0 <= choice <= 4:
            return choice
        print_error("Opción inválida. Intenta de nuevo.")


def generar_lote(scenario: str, count: int, interval: float) -> list[str]:
    """
    Genera una lista de líneas de log con el mismo comportamiento que el CLI:
    - IP fija por lote para bruteforce/portscan/beacon/dns_dga
    - Puertos únicos sin reposición para portscan
    """
    import socket

    messages = []
    fixed_ip = None
    ports = []

    if scenario == "bruteforce":
        fixed_ip = f"203.0.113.{random.randint(2, 250)}"
        print_info(f"IP atacante fija para este lote: {fixed_ip}")
    elif scenario == "portscan":
        fixed_ip = f"198.51.100.{random.randint(2, 250)}"
        print_info(f"IP atacante fija para este lote: {fixed_ip}")
        # Puertos únicos sin reposición (igual que CLI)
        if count <= len(COMMON_PORTS):
            ports = random.sample(COMMON_PORTS, k=count)
        elif count <= 65535:
            ports = random.sample(range(1, 65535), k=count)
        else:
            ports = [random.randint(1, 65535) for _ in range(count)]
    elif scenario == "beacon":
        fixed_ip = f"192.0.2.{random.randint(2, 250)}"
        print_info(f"IP de C2 externa fija para este lote: {fixed_ip}")
        print_info("Nota: usa intervalo igual o similar entre eventos para simular regularidad.")
    elif scenario == "dns_dga":
        fixed_ip = f"192.168.10.{random.randint(20, 60)}"
        print_info(f"Host interno (infectado) fijo para este lote: {fixed_ip}")

    for i in range(count):
        dport = ports[i] if scenario == "portscan" and i < len(ports) else None
        message = build_message(scenario, attacker_ip=fixed_ip, dport=dport)
        messages.append(message)

    return messages


def accion_enviar_udp(scenario: str, count: int, interval: float):
    """Acción 1: enviar por UDP al backend."""
    print_header(f"ENVIANDO {count} EVENTOS ({scenario}) A {DEFAULT_HOST}:{DEFAULT_PORT}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError as e:
        print_error(f"No se pudo crear socket UDP: {e}")
        return

    fixed_ip = None
    ports = []

    if scenario == "bruteforce":
        fixed_ip = f"203.0.113.{random.randint(2, 250)}"
        print_info(f"IP atacante fija: {fixed_ip}")
    elif scenario == "portscan":
        fixed_ip = f"198.51.100.{random.randint(2, 250)}"
        print_info(f"IP atacante fija: {fixed_ip}")
        if count <= len(COMMON_PORTS):
            ports = random.sample(COMMON_PORTS, k=count)
        elif count <= 65535:
            ports = random.sample(range(1, 65535), k=count)
        else:
            ports = [random.randint(1, 65535) for _ in range(count)]
    elif scenario == "beacon":
        fixed_ip = f"192.0.2.{random.randint(2, 250)}"
        print_info(f"IP de C2 externa fija: {fixed_ip}")
    elif scenario == "dns_dga":
        fixed_ip = f"192.168.10.{random.randint(20, 60)}"
        print_info(f"Host interno fijo: {fixed_ip}")

    print()  # línea en blanco

    try:
        for i in range(count):
            dport = ports[i] if scenario == "portscan" and i < len(ports) else None
            message = build_message(scenario, attacker_ip=fixed_ip, dport=dport)
            try:
                sock.sendto(message.encode(), (DEFAULT_HOST, DEFAULT_PORT))
            except OSError as e:
                print_error(f"Error enviando UDP: {e}")
                sock.close()
                return

            if HAS_RICH:
                console.print(f"  [dim]{i + 1}/{count}[/dim] {message}")
            else:
                print(f"  [{i + 1}/{count}] {message}")

            if i < count - 1:
                time.sleep(interval)

        print()
        print_success(f"Lote enviado. Verifica en dashboard: http://localhost:8501")
        print_info("O consulta API: curl http://localhost:8000/events")

    except KeyboardInterrupt:
        print_warn("\nInterrumpido por usuario.")
    finally:
        sock.close()


def accion_mostrar_cli(scenario: str, count: int, interval: float):
    """Acción 2: mostrar comando CLI equivalente."""
    print_header("COMANDO CLI EQUIVALENTE")

    cmd = (
        f"python scripts/generate_fake_logs.py "
        f"--scenario {scenario} "
        f"--count {count} "
        f"--interval {interval} "
        f"--host {DEFAULT_HOST} "
        f"--port {DEFAULT_PORT}"
    )

    if HAS_RICH:
        console.print(Panel(cmd, title="Comando listo para copiar", border_style="green"))
    else:
        print(f"\n{cmd}\n")

    print_info("Copia y ejecuta en otra terminal si lo necesitas.")


def accion_copiar_clipboard(scenario: str, count: int, interval: float):
    """Acción 3: generar logs y copiar al portapapeles."""
    print_header("COPIAR LOGS AL PORTAPAPELES")

    messages = generar_lote(scenario, count, interval)
    block = "\n".join(messages)

    if HAS_CLIPBOARD:
        try:
            pyperclip.copy(block)
            print_success(f"¡{count} líneas copiadas al portapapeles!")
            print_info("Pégalas en la ingesta manual del dashboard (📥 Ingesta manual).")
        except Exception as e:
            print_warn(f"No se pudo copiar al portapapeles: {e}")
            print_info("Mostrando en pantalla como alternativa:")
            _print_block(block)
    else:
        print_warn("pyperclip no instalado. No se puede acceder al portapapeles.")
        print_info("Instala con: pip install pyperclip")
        print_info("Mostrando en pantalla:")
        _print_block(block)


def _print_block(block: str):
    if HAS_RICH:
        console.print(Panel(block, title="Logs generados", border_style="blue", expand=False))
    else:
        print(f"\n{'-'*60}")
        print(block)
        print(f"{'-'*60}\n")


def accion_guardar_archivo(scenario: str, count: int, interval: float):
    """Acción 4: guardar logs en archivo."""
    print_header("GUARDAR LOGS EN ARCHIVO")

    messages = generar_lote(scenario, count, interval)
    block = "\n".join(messages)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fake_logs_{scenario}_{timestamp}.txt"
    filepath = OUT_DIR / filename

    try:
        filepath.write_text(block + "\n", encoding="utf-8")
        print_success(f"Archivo guardado: {filepath.resolve()}")
        print_info(f"{count} líneas escritas (UTF-8, una línea por evento).")
        print_info("Sube este archivo en la ingesta manual del dashboard (Ingesta manual -> Subir archivo).")
    except OSError as e:
        print_error(f"No se pudo escribir el archivo: {e}")


def main_loop():
    """Bucle principal de la TUI."""
    while True:
        try:
            # 1. Menú escenario
            escenario = menu_escenario()
            if escenario is None:
                print_info("Saliendo. ¡Hasta luego!")
                break

            # 2. Cantidad
            count = ask_count()
            if count is None:
                continue

            # 3. Intervalo (opcional, con default)
            interval = ask_interval(default=DEFAULT_INTERVAL, scenario=escenario)
            if interval is None:
                continue

            # 4. Menú acción
            while True:
                accion = menu_accion()
                if accion == 0:
                    break  # volver a menú escenario
                elif accion == 1:
                    accion_enviar_udp(escenario, count, interval)
                elif accion == 2:
                    accion_mostrar_cli(escenario, count, interval)
                elif accion == 3:
                    accion_copiar_clipboard(escenario, count, interval)
                elif accion == 4:
                    accion_guardar_archivo(escenario, count, interval)

                # Preguntar si quiere otra acción con el mismo lote
                if HAS_RICH:
                    otra = Prompt.ask(
                        "\n¿Otra acción con este mismo escenario/count?",
                        choices=["s", "n"],
                        default="n"
                    )
                else:
                    otra = input("\n¿Otra acción con este mismo escenario/count? [s/N]: ").strip().lower()

                if otra != "s":
                    break

        except KeyboardInterrupt:
            print_info("\nInterrumpido. Saliendo...")
            break
        except EOFError:
            print_info("\nSaliendo...")
            break


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print_info("\n¡Hasta luego!")
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        sys.exit(1)