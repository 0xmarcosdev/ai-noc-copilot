"""
Generador de logs sintéticos con formato REAL de filterlog de pfSense
(verificado contra la gramática BNF oficial de Netgate y el código fuente
`syslog.inc` de pfSense -- ver docs/pfsense-filterlog-format.md).

Orden de campos IPv4 confirmado:
  rulenum,subrulenum,anchor,tracker,realint,reason,action,direction,
  version,tos,ecn,ttl,id,offset,flags,protoid,prototext,
  length,srcip,dstip,
  [TCP/UDP: srcport,dstport,datalen]
  [solo TCP: tcpflags,seq,ack,window,urg,options]

Uso:
    python scripts/generate_fake_logs.py --host 127.0.0.1 --port 5514 --count 15
    python scripts/generate_fake_logs.py --scenario bruteforce --count 20
"""
import argparse
import random
import socket
import time
from datetime import datetime, timezone

INTERFACES = ["igb0", "igb1", "em0"]


def _base_fields(rulenum, action, direction):
    # rulenum,subrulenum,anchor,tracker,realint,reason,action,direction,version
    tracker = 1000000000 + random.randint(100, 999)
    iface = random.choice(INTERFACES)
    return f"{rulenum},,,{tracker},{iface},match,{action},{direction},4"


def build_tcp_line(action="block", direction="in", src=None, dst=None,
                    sport=None, dport=22, flags="S"):
    src = src or f"{random.choice([198, 203, 45])}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    dst = dst or f"192.168.10.{random.randint(2, 250)}"
    sport = sport or random.randint(1024, 65535)
    ttl = random.randint(48, 64)
    ident = random.randint(0, 65535)
    base = _base_fields(random.randint(1, 20), action, direction)
    # tos,ecn,ttl,id,offset,flags(ip),protoid,prototext
    ipv4 = f"0x0,,{ttl},{ident},0,DF,6,tcp"
    length = random.randint(40, 60)
    seq = random.randint(10**7, 10**9)
    # length,srcip,dstip,srcport,dstport,datalen,tcpflags,seq,ack,window,urg,options
    tail = f"{length},{src},{dst},{sport},{dport},0,{flags},{seq},,65535,,mss;nop;wscale"
    return f"filterlog: {base},{ipv4},{tail}"


def build_udp_line(action="block", direction="in", src=None, dst=None,
                    sport=None, dport=53):
    src = src or f"{random.randint(1,223)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    dst = dst or f"192.168.10.{random.randint(2, 250)}"
    sport = sport or random.randint(1024, 65535)
    ttl = random.randint(48, 64)
    ident = random.randint(0, 65535)
    base = _base_fields(random.randint(1, 20), action, direction)
    ipv4 = f"0x0,,{ttl},{ident},0,DF,17,udp"
    length = random.randint(40, 90)
    tail = f"{length},{src},{dst},{sport},{dport},{length - 28}"
    return f"filterlog: {base},{ipv4},{tail}"


def scenario_normal(attacker_ip=None):
    """Mezcla de tráfico normal: algunos pass, algunos block sueltos."""
    choices = [
        lambda: build_tcp_line(action="pass", direction="out", dport=443),
        lambda: build_tcp_line(action="block", direction="in", dport=random.choice([3389, 445, 8080])),
        lambda: build_udp_line(action="pass", direction="out", dport=53),
        lambda: "openvpn[12345]: Inactivity timeout (--ping-restart), restarting",
    ]
    return random.choice(choices)()


def scenario_bruteforce(attacker_ip=None):
    """Mismo origen (fijo para todo el lote), múltiples bloqueos seguidos al puerto 22."""
    attacker_ip = attacker_ip or f"203.0.113.{random.randint(2, 250)}"
    target = "192.168.10.5"
    return build_tcp_line(action="block", direction="in", src=attacker_ip,
                           dst=target, dport=22, flags="S")


def scenario_portscan(attacker_ip=None):
    """Mismo origen (fijo para todo el lote), puertos destino distintos."""
    attacker_ip = attacker_ip or f"198.51.100.{random.randint(2, 250)}"
    target = "192.168.10.8"
    dport = random.choice([21, 23, 25, 80, 139, 443, 3306, 3389, 8080])
    return build_tcp_line(action="block", direction="in", src=attacker_ip,
                           dst=target, dport=dport, flags="S")


SCENARIOS = {
    "normal": scenario_normal,
    "bruteforce": scenario_bruteforce,
    "portscan": scenario_portscan,
}


def build_message(scenario: str, attacker_ip: str | None) -> str:
    body = SCENARIOS[scenario](attacker_ip)
    timestamp = datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")
    return f"{timestamp} pfsense-prod {body}"


def main():
    parser = argparse.ArgumentParser(description="Envía logs sintéticos de pfSense (formato filterlog real) por UDP")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5514)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default="normal",
                         help="normal = mezcla variada | bruteforce = SSH brute-force | portscan = escaneo de puertos")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    fixed_ip = None
    if args.scenario == "bruteforce":
        fixed_ip = f"203.0.113.{random.randint(2, 250)}"
        print(f"IP atacante fija para este lote: {fixed_ip}\n")
    elif args.scenario == "portscan":
        fixed_ip = f"198.51.100.{random.randint(2, 250)}"
        print(f"IP atacante fija para este lote: {fixed_ip}\n")

    for i in range(args.count):
        message = build_message(args.scenario, attacker_ip=fixed_ip)
        sock.sendto(message.encode(), (args.host, args.port))
        print(f"[{i + 1}/{args.count}] {message}")
        time.sleep(args.interval)

    print("\nListo. Verifica con: curl http://localhost:8000/events")


if __name__ == "__main__":
    main()