# Diagnostico de Latencia del LLM

> Fecha: 24 ago 2026 | Modelo: my-qwen-3b:latest (Qwen 2.5 3B Q4_K_M)
> Plataforma: Windows, Python 3.12, Ollama nativo (no Docker)

## 1. Setup

- **Modelo**: my-qwen-3b:latest (~2.1 GB, quantizacion Q4_K_M)
- **Prompt de prueba**: log de filterlog de pfSense (156 chars, 438 tokens en prompt)
- **Parametros LLM**: temperature=0.1, format=json, keep_alive=10m, num_predict=400
- **Plan de energia**: Balanced (GUID: 381b4222-f694-41f0-9685-ff5bb260df2e)
- **Estado de bateria**: Enchufado, 98% carga (cargando)

## 2. Resultados

### Tabla de metricas

| Escenario | total | load | prompt_eval | prompt_tokens | gen | gen_tokens | tok/s | wall-clock |
|---|---|---|---|---|---|---|---|---|
| 1. Cold start (post ollama stop) | 36.91s | 15.62s | 2.62s | 438 | 18.63s | 103 | 5.5 | 38.06s |
| 2. Hot (modelo ya cargado) | 19.84s | 0.66s | 0.21s | 438 | 18.92s | 99 | 5.2 | 20.84s |
| 3. Keep alive test (6 min despues) | 14.23s | 0.53s | 0.62s | 438 | 13.05s | 98 | 7.5 | 14.81s |
| 4. Concurrente (ollama ps) | 18.00s | 0.53s | 0.15s | 438 | 17.30s | 125 | 7.2 | 18.62s |

### Output de ollama ps (llamada 4)

    NAME                 ID              SIZE      PROCESSOR          CONTEXT    UNTIL
    my-qwen-3b:latest    707dcea79925    2.4 GB    74%/26% CPU/GPU    4096       9 minutes from now

- **CPU/GPU**: 74% CPU / 26% GPU (Ollama usa CPU mayoritariamente)
- **Memoria**: 2.4 GB residente
- **Contexto**: 4096 tokens

## 3. Analisis

### Desglose de fases (usando metricas de Ollama)

**Fase 1 - Load (carga del modelo):**
- Cold start: 15.62s (primera vez, carga de disco a RAM)
- Hot: 0.53-0.66s (ya residente en memoria)
- La carga es ~30x mas rapida cuando el modelo esta caliente

**Fase 2 - Prompt evaluation (evaluacion del prompt):**
- 438 tokens de prompt evaluados en 0.15-2.62s
- Cold start es ~17x mas lento (2.62s vs 0.15s) por caching de CPU
- Varia bastante entre llamadas (0.15s a 2.62s)

**Fase 3 - Generacion (tokens de respuesta):**
- 98-125 tokens generados en 13-19s
- Velocidad: 5.2-7.5 tok/s (CPU-bound, 74% CPU)
- La generacion es la fase dominante (~70-85% del tiempo total)

### Keep alive: funciona

- Llamada 2 a llamada 3: 6 minutos de inactividad
- load_duration bajo (0.53s), confirma que el modelo NO se descargo
- keep_alive=10m funciona correctamente (el default de Ollama es 5m)

### Donde se va el tiempo

    Llamada 1 (cold start, 38s):
      load:    15.62s (41%)  <-- cold start, carga desde disco
      prompt:   2.62s (7%)
      gen:     18.63s (49%)  <-- generacion de ~100 tokens

    Llamada 2 (hot, 21s):
      load:     0.66s (3%)   <-- ya cargado
      prompt:   0.21s (1%)
      gen:     18.92s (91%)  <-- generacion domina completamente

**Conclusion**: con el modelo caliente, ~91% del tiempo es generacion pura.
El bottleneck es CPU (74% CPU, solo 26% GPU). Con GPU plena, la generacion
seria significativamente mas rapida.

## 4. Siguientes pasos posibles (con datos)

1. **Cold start (15s load)**: mitigable con keep_alive largo o precarga
   al inicio del backend. Ya configurado a 10m, funciona.

2. **Generacion lenta (5-7 tok/s)**: el modelo Q4_K_M corre mayormente en
   CPU. Opciones:
   - Usar un modelo mas pequeno (1.5B en vez de 3B) si la calidad es aceptable
   - Verificar si CUDA esta disponible y configurado (ollama ps muestra 26% GPU)
   - Considerar OLLAMA_NUM_GPU para forzar mas capas en GPU

3. **num_predict=400**: es un techo duro. Las respuestas actuales usan
   ~100 tokens, lejos del limite. Podria bajarse a 200 para ganar margen
   sin riesgo.

4. **Prompt mas corto**: el prompt actual usa 438 tokens. Un prompt mas
   conciso reduciria prompt_eval pero el impacto es minimo (~2s en cold,
   <0.5s en hot).
