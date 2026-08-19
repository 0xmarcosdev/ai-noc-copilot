"""
Extracción de consultas DNS desde logs de pfSense -- soporta los dos
motores posibles: DNS Resolver (Unbound) y DNS Forwarder (dnsmasq).
Formato verificado con Perplexity contra la documentación oficial de
Netgate (docs.netgate.com/pfsense/troubleshooting/dns-queries.html) --
ver docs/ai-sessions/ para la investigación completa.

A diferencia de filterlog, estos NO son CSV -- son texto libre con un
formato distinto por cada daemon:

Unbound:  "unbound[96103]: [96103:0] info: 192.168.1.100 daisy.ubuntu.com. A IN"
dnsmasq:  "dnsmasq[1068]: query[A] daisy.ubuntu.com from 192.0.2.5"
"""
import re
from typing import Optional

UNBOUND_DNS_RE = re.compile(
    r"unbound(?:\[\d+\])?:\s*\[\d+:\d+\]\s+info:\s+"
    r"(?P<client_ip>[\d.]+)\s+(?P<domain>[\w.\-]+?)\.\s+"
    r"(?P<qtype>\w+)\s+(?P<qclass>\w+)"
)

DNSMASQ_DNS_RE = re.compile(
    r"dnsmasq(?:\[\d+\])?:\s*query\[(?P<qtype>\w+)\]\s+"
    r"(?P<domain>[\w.\-]+)\s+from\s+(?P<client_ip>[\d.]+)"
)


def extract_dns_query(raw_message: str) -> Optional[dict]:
    """
    Devuelve {"client_ip": ..., "domain": ..., "qtype": ...} si la línea
    es una consulta DNS reconocible (Unbound o dnsmasq), o None si no lo es
    (ej. es una línea de filterlog o de otro proceso).
    """
    match = UNBOUND_DNS_RE.search(raw_message)
    if match:
        return {
            "client_ip": match.group("client_ip"),
            "domain": match.group("domain").rstrip("."),
            "qtype": match.group("qtype"),
        }

    match = DNSMASQ_DNS_RE.search(raw_message)
    if match:
        return {
            "client_ip": match.group("client_ip"),
            "domain": match.group("domain").rstrip("."),
            "qtype": match.group("qtype"),
        }

    return None
