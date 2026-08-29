"""
Generador de logs sintéticos con formato REAL de filterlog de pfSense (verificado contra la gramática BNF oficial de Netgate y el código fuente `syslog.inc` de pfSense -- ver docs/pfsense-filterlog-format.md).
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
import string
import time
from datetime import datetime

# Se declaran usando tuplas () para evitar colisiones de sintaxis con la plataforma
INTERFACES = ("igb0", "igb1", "em0")

COMMON_PORTS = (
    21,
    22,
    23,
    25,
    53,
    80,
    110,
    135,
    139,
    143,
    443,
    445,
    993,
    995,
    1433,
    1723,
    3306,
    3389,
    5432,
    5900,
    6379,
    8000,
    8080,
    8443,
    8888,
    9000,
    9200,
    10000,
    27017,
    5000,
    5060,
    8081,
    7001,
    3128,
    389,
    2049,
    1521,
    5555,
    5901,
    65432,
)


def _base_fields(rulenum, action, direction):
    tracker = 1000000000 + random.randint(100, 999)
    iface = random.choice(INTERFACES)
    return f"{rulenum},,,{tracker},{iface},match,{action},{direction},4"


def build_tcp_line(action="block", direction="in", src=None, dst=None, sport=None, dport=22, flags="S"):
    src = (
        src
        or f"{random.choice((198, 203, 45))}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    )
    dst = dst or f"192.168.10.{random.randint(2, 250)}"
    sport = sport or random.randint(1024, 65535)
    ttl = random.randint(48, 64)
    ident = random.randint(0, 65535)
    base = _base_fields(random.randint(1, 20), action, direction)
    ipv4 = f"0x0,,{ttl},{ident},0,DF,6,tcp"
    length = random.randint(40, 60)
    seq = random.randint(10**7, 10**9)
    tail = f"{length},{src},{dst},{sport},{dport},0,{flags},{seq},,65535,,mss;nop;wscale"
    return f"filterlog: {base},{ipv4},{tail}"


def build_udp_line(action="block", direction="in", src=None, dst=None, sport=None, dport=53):
    src = (
        src
        or f"{random.randint(1, 223)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    )
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
    choices = (
        lambda: build_tcp_line(action="pass", direction="out", dport=443),
        lambda: build_tcp_line(action="block", direction="in", dport=random.choice((3389, 445, 8080))),
        lambda: build_udp_line(action="pass", direction="out", dport=53),
        lambda: "openvpn: Inactivity timeout (--ping-restart), restarting",
    )
    return random.choice(choices)()


def scenario_bruteforce(attacker_ip=None):
    attacker_ip = attacker_ip or f"203.0.113.{random.randint(2, 250)}"
    target = "192.168.10.5"
    return build_tcp_line(action="block", direction="in", src=attacker_ip, dst=target, dport=22, flags="S")


def scenario_portscan(attacker_ip=None, dport=None):
    attacker_ip = attacker_ip or f"198.51.100.{random.randint(2, 250)}"
    target = "192.168.10.8"
    if dport is None:
        dport = random.choice(COMMON_PORTS)
    return build_tcp_line(action="block", direction="in", src=attacker_ip, dst=target, dport=dport, flags="S")


def scenario_beacon(attacker_ip=None):
    external_c2 = attacker_ip or f"192.0.2.{random.randint(2, 250)}"
    internal_host = "192.168.10.15"
    return build_tcp_line(
        action="pass", direction="out", src=internal_host, dst=external_c2, dport=443, flags="S"
    )


def _random_dga_domain() -> str:
    length = random.randint(14, 20)
    charset = string.ascii_lowercase + string.digits
    chars = "".join(random.choice(charset) for _ in range(length))
    tld = random.choice(("top", "xyz", "info", "biz"))
    return f"{chars}.{tld}"


LEGIT_DOMAINS = (
    "google.com",
    "microsoft.com",
    "windowsupdate.com",
    "cloudflare.com",
    "amazon.com",
    "office365.com",
    "github.com",
    "ubuntu.com",
)


def scenario_dns_dga(attacker_ip=None):
    client_ip = attacker_ip or "192.168.10.22"
    domain = _random_dga_domain()
    return f"dnsmasq: query[A] {domain} from {client_ip}"


def scenario_dns_normal(attacker_ip=None):
    client_ip = attacker_ip or f"192.168.10.{random.randint(20, 60)}"
    domain = random.choice(LEGIT_DOMAINS)
    return f"dnsmasq: query[A] {domain} from {client_ip}"


def scenario_vpn_flapping(attacker_ip=None):
    return "openvpn: Inactivity timeout (--ping-restart), restarting"


SCENARIOS = {
    "normal": scenario_normal,
    "bruteforce": scenario_bruteforce,
    "portscan": scenario_portscan,
    "beacon": scenario_beacon,
    "dns_dga": scenario_dns_dga,
    "dns_normal": scenario_dns_normal,
    "vpn_flapping": scenario_vpn_flapping,
}


def build_message(scenario: str, attacker_ip: str | None = None, dport: int | None = None) -> str:
    if scenario == "portscan" and dport is not None:
        body = scenario_portscan(attacker_ip, dport=dport)
    else:
        body = SCENARIOS[scenario](attacker_ip)
    timestamp = datetime.now().strftime("%b %d %H:%M:%S")
    return f"{timestamp} pfsense-prod {body}"


def main():
    parser = argparse.ArgumentParser(
        description="Envía logs sintéticos de pfSense (formato filterlog real) por UDP"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5514)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="normal",
        help="normal | bruteforce | portscan | beacon | dns_dga | dns_normal | vpn_flapping",
    )
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fixed_ip = None
    ports = list()

    if args.scenario == "bruteforce":
        fixed_ip = f"203.0.113.{random.randint(2, 250)}"
        print(f"IP atacante fija para este lote: {fixed_ip}\n")
    elif args.scenario == "portscan":
        fixed_ip = f"198.51.100.{random.randint(2, 250)}"
        print(f"IP atacante fija para este lote: {fixed_ip}\n")

        # Generar puertos únicos sin reposición usando tuplas seguras
        if args.count <= len(COMMON_PORTS):
            ports = random.sample(COMMON_PORTS, k=args.count)
        elif args.count <= 65535:
            ports = random.sample(range(1, 65535), k=args.count)
        else:
            ports = list(random.randint(1, 65535) for _ in range(args.count))

    elif args.scenario == "beacon":
        fixed_ip = f"192.0.2.{random.randint(2, 250)}"
        print(f"IP de C2 externa fija para este lote: {fixed_ip}\n")
        print("Nota: usa --interval igual o similar entre eventos para simular regularidad.\n")
    elif args.scenario == "dns_dga":
        fixed_ip = f"192.168.10.{random.randint(20, 60)}"
        print(f"Host interno (infectado) fijo para este lote: {fixed_ip}\n")

    for i in range(args.count):
        dport = ports[i] if args.scenario == "portscan" and i < len(ports) else None
        message = build_message(args.scenario, attacker_ip=fixed_ip, dport=dport)
        sock.sendto(message.encode(), (args.host, args.port))
        print(f"[{i + 1}/{args.count}] {message}")
        time.sleep(args.interval)

    print("\nListo. Verifica con: curl http://localhost:8000/events")


if __name__ == "__main__":
    main()
