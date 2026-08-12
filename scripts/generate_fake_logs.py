"""
Generador de logs sintéticos con formato aproximado de pfSense (filterlog +
mensajes de OpenVPN), enviados por UDP al listener local.

Uso:
    python scripts/generate_fake_logs.py --host 127.0.0.1 --port 5514 --count 15

Por qué existe: para desarrollar y probar el pipeline completo
(ingesta -> BD -> "Explicar con IA" -> dashboard) SIN necesitar un pfSense
real disponible. El formato de abajo es una aproximación razonable del
formato real de filterlog de pfSense -- pendiente de verificar con fuente
oficial (tarea asignada a Perplexity, ver conversación). Cuando se
confirme el formato exacto, ajustar SAMPLE_LOGS aquí.
"""
import argparse
import random
import socket
import time
from datetime import datetime

# Aproximación del formato filterlog de pfSense:
# <fecha> <host> filterlog: <regla>,,,<interfaz>,<accion>,<direccion>,
#   <version_ip>,...,<protocolo>,<ip_origen>,<ip_destino>,<puerto_origen>,<puerto_destino>
SAMPLE_LOGS = [
    # Bloqueo simple, tráfico normal descartado por regla default-deny
    "filterlog: 5,,,1000000103,igb0,match,block,in,4,0x0,,64,0,0,DF,6,tcp,60,"
    "203.0.113.45,192.168.10.20,51823,3389,0,S,,,,,",
    # Múltiples intentos SSH en poco tiempo (patrón de fuerza bruta)
    "filterlog: 5,,,1000000103,igb0,match,block,in,4,0x0,,64,0,0,DF,6,tcp,60,"
    "198.51.100.77,192.168.10.5,44211,22,0,S,,,,,",
    # Conexión permitida normal (tráfico legítimo, para contraste)
    "filterlog: 10,,,1000000104,igb1,match,pass,out,4,0x0,,64,0,0,DF,6,tcp,60,"
    "192.168.10.15,8.8.8.8,55123,443,0,S,,,,,",
    # Caída de túnel VPN
    "openvpn[12345]: Inactivity timeout (--ping-restart), restarting",
    # Escaneo de puertos: muchos puertos distintos, mismo origen
    "filterlog: 5,,,1000000103,igb0,match,block,in,4,0x0,,64,0,0,DF,6,tcp,60,"
    "203.0.113.99,192.168.10.8,{sport},{dport},0,S,,,,,",
]


def build_message() -> str:
    template = random.choice(SAMPLE_LOGS)
    if "{sport}" in template:
        template = template.format(sport=random.randint(1024, 65535), dport=random.randint(1, 1024))
    timestamp = datetime.now().strftime("%b %d %H:%M:%S")
    return f"{timestamp} pfSense-lab {template}"


def main():
    parser = argparse.ArgumentParser(description="Envía logs sintéticos de pfSense por UDP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5514)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.5, help="segundos entre envíos")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(args.count):
        message = build_message()
        sock.sendto(message.encode(), (args.host, args.port))
        print(f"[{i + 1}/{args.count}] enviado: {message}")
        time.sleep(args.interval)

    print("\nListo. Verifica con: curl http://localhost:8000/events")


if __name__ == "__main__":
    main()
