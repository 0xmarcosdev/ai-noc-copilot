"""
Heurísticas para detectar dominios potencialmente generados
algorítmicamente (DGA -- Domain Generation Algorithm), típico de malware
que genera dominios de C2 pseudoaleatorios para evadir listas negras.

Esto es una heurística determinista, NO un veredicto del LLM -- el LLM
solo redacta la explicación sobre lo que esta función ya detectó (ver
SPEC.md, principio de diseño: la detección es determinista, el LLM explica).

Referencia conceptual: dominios legítimos tienden a tener baja entropía
(patrones pronunciables, palabras de diccionario); dominios DGA tienden a
alta entropía (secuencias pseudoaleatorias de caracteres). Es una señal,
no una prueba -- sin acceso a listas de amenazas en vivo (air-gapped), no
hay forma de confirmar con certeza que un dominio es malicioso.
"""
import math
from collections import Counter


def shannon_entropy(s: str) -> float:
    """Calcula la entropía de Shannon de una cadena.

    Args:
        s: Cadena de texto (ej. nombre de dominio).

    Returns:
        Entropía en bits por carácter. 0.0 si la cadena está vacía.
    """
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def looks_like_dga(domain: str, entropy_threshold: float = 3.5) -> bool:
    """
    Revisa DOS lugares distintos del dominio, porque el patrón varía:
    1. El dominio de segundo nivel (SLD) -- típico de malware DGA clásico
       (ej. "kj3h9fkj2h.com").
    2. El subdominio más a la izquierda -- típico de túneles DNS /
       exfiltración de datos, que codifican información ahí en vez de
       en el dominio registrado (ej. "aGVsbG8gd29ybGQ.tunnel.evil.net").

    Los guiones se ignoran para el cálculo de entropía (palabras legítimas
    con guión, como "actualizacion-windows", no deben marcarse como DGA
    solo por tener más variedad de caracteres).

    Args:
        domain: Nombre de dominio completo.
        entropy_threshold: Umbral de entropía (bits/carácter) para marcar como sospechoso.

    Returns:
        True si el dominio parece generado algorítmicamente, False en caso contrario.
    """
    labels = [l for l in domain.lower().strip(".").split(".") if l]
    if len(labels) < 2:
        return False

    second_level = labels[-2].replace("-", "")
    sld_flag = len(second_level) >= 6 and shannon_entropy(second_level) >= entropy_threshold

    leftmost = labels[0].replace("-", "")
    subdomain_flag = len(leftmost) >= 10 and shannon_entropy(leftmost) >= entropy_threshold

    return sld_flag or subdomain_flag