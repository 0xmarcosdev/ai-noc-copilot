# Sesión 17 — 27 ago 2026 — Métricas rendimiento LLM y pestaña Rendimiento

**Asistente**: Gemini Flash  
**Fase**: 5.10 (Métricas y Diagnóstico de Rendimiento LLM)  
**Momento relacionado**: Trade-offs hardware (documentado en SPEC §9, dashboard tab Rendimiento)

---

## Análisis y Diagnóstico de Latencia

### Evaluación de Hardware
- **GPU**: NVIDIA GeForce MX150 con 2 GB VRAM
- **Modelo**: Qwen 3.4B Q4_K_M (~2.4 GB en memoria)
- **Cuello de botella identificado**: Ollama descarga 74% de capas a CPU y 26% a GPU por restricción física de VRAM
- **Rendimiento resultante**: ~5.2 tok/s (~18.9s por inferencia)

### Conclusión Arquitectónica
- El código está completamente optimizado: reutilización de cliente HTTP, `keep_alive=10m`, mediciones por fases en tabla `LLMTiming`
- La limitación es **estrictamente física** (VRAM insuficiente para modelo 3.4B)
- Además: la detección de anomalías de seguridad es determinista y **no depende de la velocidad del LLM**

---

## Cambios Implementados

### 1. Backend (`backend/app/main.py`)
- Agregado endpoint `@app.get("/performance/stats")` que consulta tabla persistente `LLMTiming`
- Expone:
  - Resumen métricas acumuladas: total llamadas, tiempo medio inferencia, tokens/segundo
  - Desglose hardware/offload: GPU, arquitectura, modelo actual, límite VRAM, memoria modelo, split CPU/GPU
  - Matriz de trade-offs (4 opciones):
    - Modelo actual (Qwen 3.4B Q4_K_M) — 2.4GB VRAM, ~5.2 tok/s, calidad alta
    - **Opción A (recomendada)**: Qwen 2.5 1.5B Q4_K_M — 1.1GB VRAM, ~30-40 tok/s, calidad muy buena para clasificación logs
    - Opción B: Cuantización Q3_K_M (3.4B) — 1.7GB VRAM, ~15s, calidad media-alta
    - Opción C: CPU pura Q8_0 (3.4B) — 0GB VRAM, ~5-7 tok/s, calidad alta

### 2. Frontend (`frontend/dashboard.py`)
- Creado cuarto tab `⚡ Rendimiento`
- Visualización KPIs principales en 4 columnas
- Panel diagnóstico hardware + cuello de botella
- Tarjetas visuales trade-offs con badge de recomendación
- Gráfico dispersión/línea temporal interactivo (Plotly): tiempo generación por llamada + tabla expandible historial reciente

### 3. Validación
- `pytest tests -v` → 37/37 tests pasando

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `backend/app/main.py` | GET /performance/stats, matriz trade-offs hardware |
| `frontend/dashboard.py` | Tab Rendimiento: KPIs, diagnóstico, trade-offs, gráfico Plotly historial |