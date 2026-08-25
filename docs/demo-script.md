# Guion de demo — AI-NOC Copilot

## Pre-requisitos antes de grabar

### Checklist pre-grabación

- [ ] Ollama corriendo: `curl http://localhost:11434/api/tags` → debe devolver la lista de modelos
- [ ] Backend corriendo: `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] Frontend corriendo: abrir http://localhost:8501 en el navegador
- [ ] Base de datos limpia (opcional pero recomendado): borrar `backend/data/ai_noc.db` y reiniciar el backend para partir de cero
- [ ] Terminal de PowerShell visible con los logs del backend (para mostrar la ingesta en tiempo real)
- [ ] Navegador con el dashboard abierto en pantalla completa (ocultar barras de favoritos)
- [ ] Desactivar notificaciones del sistema y del navegador durante la grabación

---

## Secuencia de demo (8–10 minutos)

### Escena 1 — Introducción y contexto (30 segundos)

> "Este es AI-NOC Copilot, un asistente local y air-gapped para análisis de logs de pfSense. Funciona completamente offline: ingesta de logs, correlación de eventos, detección de anomalías y explicación en lenguaje natural — todo sin conexión a internet."

Mostrar la arquitectura en el SPEC.md o una diapositiva rápida si se desea.

---

### Escena 2 — Ingesta de logs de fuerza bruta (1 minuto)

Abrir una terminal y ejecutar:

```powershell
cd D:\AiProject\ai-noc-copilot
python scripts/generate_fake_logs.py --scenario bruteforce --count 10
```

**Qué mostrar:** el output del script indicando 10 eventos generados con la misma IP atacante fija.

Explicar brevemente:
> "Estos 10 registros simulan un ataque de fuerza bruta SSH contra el pfSense. Cada uno es un evento individual — por sí solo, no parece amenaza."

---

### Escena 3 — Consultar eventos en el dashboard (1 minuto)

1. Refrescar el dashboard (F5 o click en "Rerun").
2. Mostrar la tabla de eventos: los 10 eventos aparecen con severity "low" o "info".
3. Explicar:
   > "Cada evento se analizó individualmente con el LLM local (Ollama, modelo Qwen 3B). Sin contexto de los demás, el sistema clasifica cada intento como severidad baja — exactamente como lo haría un analista humano viendo un solo evento aislado."

---

### Escena 4 — Correlación de eventos (2 minutos)

1. Hacer click en el botón **"Correlacionar eventos sin analizar"** en el dashboard.
2. Esperar el procesamiento (10–30 segundos según hardware).
3. Explicar lo que ocurre en background:
   > "El sistema agrupa los 10 eventos por la misma IP atacante real (extraída del raw_message del syslog), detecta que el 100% va al mismo puerto destino, y clasifica el patrón como 'fuerza bruta'. Luego envía el grupo completo al LLM con ese contexto."

4. Mostrar los resultados:
   - Severity sube de "low" a **"high"** — el cambio de contexto es evidente.
   - El patrón clasificado como `fuerza_bruta` aparece en la sección de histórico.
   - La IP atacante es la misma en todos los eventos del grupo.

5. Ir a la sección **"Histórico de correlación"** (scroll hacia abajo) y mostrar el grupo persistido con:
   - Ícono 🎯 (fuerza bruta)
   - IP atacante
   - Severidad
   - Ventana temporal
   - IDs de eventos

---

### Escena 5 — Análisis individual de un evento (1 minuto)

1. En la tabla de eventos, seleccionar un evento del grupo correlacionado.
2. Hacer click en **"Explicar con AI"**.
3. Mostrar la explicación en lenguaje natural que genera el LLM:
   > "El LLM recibe el evento con el contexto del grupo completo (patrón de fuerza bruta, IP, puertos) y genera una explicación detallada en español."

---

### Escena 6 — Ingesta manual y exportación (1.5 minutos)

**Parte A — Ingesta manual (30 segundos):**
1. Pegar 2–3 líneas de log real de pfSense (sanitizado) en el expander "Ingesta manual".
2. Hacer click en "Ingerir".
3. Mostrar que los nuevos eventos aparecen en la tabla.

**Parte B — Exportar (1 minuto):**
1. Mostrar los botones de descarga CSV y JSON.
2. Descargar un archivo y abrirlo brevemente para mostrar el formato.
3. Generar un reporte on-demand y descargar el Markdown resultante.

---

### Escena 7 — Resumen estadístico (1 minuto)

1. Scroll hacia arriba en el dashboard para mostrar los gráficos:
   - Pie chart de severidad (barras de colores)
   - Barras de distribución por tipo de evento
   - Serie temporal de eventos por hora
2. Explicar brevemente:
   > "Todo determinista — sin pasar por el LLM — para que sea rápido y consistente."

---

### Escena 8 — Cierre (30 segundos)

> "AI-NOC Copilot demuestra que un equipo con un procesador estándar puede ejecutar un SOC copilot completamente offline: ingesta, correlación, detección de anomalías (beaconing, DGA, fuerza bruta, escaneo de puertos) y explicación en lenguaje natural. Todo el código fuente, los tests y la documentación están disponibles para revisión."

---

## Notas técnicas para la grabación

- **Tiempo del LLM**: 10–60 segundos por llamada según el hardware (el modelo Qwen 3B es ligero pero no instantáneo). No editar este tiempo — mostrarlo tal cual es parte de la demo honesta.
- **Base de datos**: si se usa la misma DB de desarrollo, los eventos de pruebas anteriores pueden estar presentes. Para una demo limpia, borrar `backend/data/ai_noc.db` antes de empezar.
- **Ollama**: si no está corriendo, las llamadas al LLM fallarán silenciosamente. Verificar con `curl http://localhost:11434/api/tags` antes de grabar.
- **Correlación**: después de ingestar los logs, SIEMPRE hacer click en "Correlacionar" antes de mostrar los resultados — sin ese paso, los eventos siguen como individuales.

## Archivos relevantes

| Archivo | Propósito |
| --- | --- |
| `scripts/generate_fake_logs.py` | Generador de logs sintéticos |
| `backend/app/main.py` | API principal (FastAPI) |
| `frontend/dashboard.py` | Dashboard Streamlit |
| `docs/SPEC.md` | Documentación técnica |
| `backend/data/ai_noc.db` | Base de datos SQLite (borrar para demo limpia) |
