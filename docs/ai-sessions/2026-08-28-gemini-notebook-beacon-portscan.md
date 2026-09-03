# Sesión 18 — 28 ago 2026 — Robustez escenarios sintéticos y exclusión mutua en API

**Asistente**: Gemini Notebook (Copiloto de IA)  
**Fase**: 5.5/5.8 (Detección extendida + Persistencia correlación)  
**Momento clave**: #5 — Conflicto correlación agrupando beaconing (pass) como fuerza bruta

---

## Diagnóstico y Problemas Encontrados

### 1. Conflicto en escenario 'beacon' (Momento clave #5)
- `/events/correlate` agrupaba eventos de beaconing (action `pass`, direction `out`) y los marcaba incorrectamente como `fuerza_bruta` debido a la baja variación de puertos destino hacia el C2
- Esto marcaba los logs como `analyzed=True`, impidiendo que `/events/detect-beaconing` los procesara

### 2. Error de desempaquetado en beaconing
- Intento previo de solucionar la concurrencia alteró el agrupamiento a clave tipo string
- Provocaba `ValueError` catastrófico al desestructurar la tupla original `(srcip, dstip, dstport)`

### 3. Inestabilidad del escenario 'portscan'
- `generate_fake_logs.py` elegía puertos con reposición (`random.choice`) de pool pequeño (9 puertos)
- Con `--count 5` (default), era común tener duplicados → ratio variación caía a zona indeterminada (0.3–0.7) → demo inconsistente

---

## Cambios Realizados

### Backend (`backend/app/main.py`)

**Filtrado estricto en `correlate_events()`**:
- Extrae metadatos conexión con `extract_connection_summary()`
- Procesa **únicamente** eventos con acción `"block"`
- Resuelve conflicto: beaconing (pass/out) ya no entra en correlación

**Restauración de Beaconing**:
- Revertida firma de agrupación en `/events/detect-beaconing` a diccionario de tuplas `(src, dst, dport)`
- Mantiene análisis de intervalos temporal intacto
- Evita errores en tiempo de ejecución

### Generador Sintético (`scripts/generate_fake_logs.py`)

- **Pool puertos ampliado**: Tupla global `COMMON_PORTS` con 40 puertos representativos de infraestructura TI
- **Muestreo sin reposición**: En escenario `portscan`, `random.sample()` genera lista puertos destino únicos
- Garantiza ratio variación consistentemente `1.0` en lotes cortos (`--count 5`) → demo 100% predecible
- Constructores adaptados para tuplas nativas (evita interferencias markdown)

### Tests (`backend/tests/test_api.py`)

- Implementado `test_correlate_ignores_pass_action_events` de forma aislada e independiente
- Confirma que paquetes `pass`/`out` **jamás** son tomados por lógica de correlación

### Especificación Técnica (`docs/SPEC.md`)

- §7 actualizado: correlación determinista solo opera sobre paquetes bloqueados (`action == "block"`)

---

## Resultados de la Sesión

- **100% tests en verde** ejecutando `pytest tests -v` en entorno virtual
- Escenarios `beacon` y `portscan` se comportan de forma predecible y excluyente sin pisarse
- Exclusión mutua en API validada: `/correlate` ve solo `block`; `/detect-beaconing` ve solo `pass/out`

---

## Decisión de Diseño / Aprendizaje Clave

**Exclusión mutua semántica en la API**: Cada detector opera sobre su dominio — correlación = eventos bloqueados (ataques activos), beaconing = conexiones salientes permitidas (posible C2). Evita falsos positivos y pisadas de estado (`analyzed=True`) entre detectores. Documentado en SPEC §7.

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `backend/app/main.py` | Filtrado estricto action="block" en correlate_events; restauración agrupamiento beaconing |
| `scripts/generate_fake_logs.py` | COMMON_PORTS (40 puertos), random.sample sin reposición en portscan |
| `backend/tests/test_api.py` | test_correlate_ignores_pass_action_events |
| `docs/SPEC.md` | §7: correlación solo sobre paquetes bloqueados |