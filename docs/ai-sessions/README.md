# Sesiones de IA — evidencia de uso

Cada archivo de esta carpeta es una sesión clave con una herramienta de IA,
exportada como texto (copiar/pegar el intercambio relevante, no hace falta
la conversación completa si es muy larga -- basta el fragmento que muestra
la contribución real). Nombre de archivo: `AAAA-MM-DD-herramienta-tema.md`.

## Índice

| Fecha | Herramienta | Tema | Contribución |
|---|---|---|---|
| 2026-08-10 | Claude | Diseño de arquitectura, evaluación de 7 propuestas | Definición del MVP, descarte de sobrealcance |
| 2026-08-11 | Perplexity | Formato filterlog de pfSense | Verificación con fuente oficial (BNF + código fuente) |
| 2026-08-12 | Qwen | Debug de rutas en Windows, bug de carpeta `data/` | Diagnóstico correcto de un bug real |
| 2026-08-16 | DeepSeek | Preguntas para el chat del dashboard | 3 preguntas + pseudocódigo, 1 incorporada al `/summary` |
| 2026-08-16 | (herramienta sin especificar) | Detección de picos con z-score | Diseño evaluado y conscientemente descartado por scope creep (ver DEVLOG) |
| 2026-08-17 | Claude | Correlación de eventos, beaconing, heurísticas DNS | Features completas de detección de patrones |

## Cómo agregar una sesión nueva

1. Copia el intercambio relevante (prompt + respuesta) a un archivo nuevo aquí.
2. Agrega una fila al índice de arriba.
3. Si la sesión se usó para el proyecto, referencia también el commit donde
   se incorporó (ej. "ver commit `abc1234`").

No hace falta capturar cada mensaje de cada conversación -- el objetivo es
mostrar evidencia real de uso de IA en decisiones concretas, no un archivo
por cada intercambio trivial.
