# BRANDING.md — Guía de identidad visual · AI-NOC Copilot

> Documento de referencia de marca para el proyecto. Cualquier cambio de UI
> (Streamlit, README, demos, slides) debe alinearse con esta guía.
> **Todo el copy de producto sigue en español** (AGENTS.md / SPEC.md).

---

## 1. Nombre del producto

| Uso | Texto |
|-----|--------|
| **Nombre canónico** | AI-NOC Copilot |
| **Nombre corto** | AI-NOC |
| **Tagline** | Copiloto local de logs de pfSense — 100 % offline |
| **Tagline alternativo (más corto)** | Seguridad de red, explicada en local |

**No usar** como nombre de producto: “AI NOC”, “AInoc”, “NOC-AI”, “pfSense Copilot” (el producto no es de Netgate).

**Contexto de marca:** copiloto de un NOC (Network Operations Center) que trabaja **air-gapped**: recibe syslog de pfSense, detecta patrones de forma determinista y pide al LLM local solo la explicación. La identidad debe transmitir *control local, claridad operativa y vigilancia*, no “startup de IA generativa en la nube”.

---

## 2. Personalidad de marca (tono)

| Atributo | Sí | No |
|----------|----|----|
| Tono | Técnico, directo, calmado | Hype, “revolutionary AI” |
| Voz | Operador senior que explica | Chatbot genérico / emojis excesivos |
| Confianza | Offline, datos que no salen de la red | Promesas de magia o autonomía total |
| Humor | Seco, ocasional | Memes o informalidad forzada |

En UI y mensajes de error preferir:

- “Backend no disponible. ¿Está corriendo uvicorn?”
- “No se detectaron patrones por encima del umbral.”

Evitar:

- “¡Oops! Algo salió mal 😅”
- “Nuestra IA pensó que…”

---

## 3. Logo y símbolo

### Concepto

**Símbolo:** un **radar / anillo de vigilancia** minimalista con un **nodo central** (el copiloto) y 2–3 “blips” en el anillo (eventos). Lectura secundaria: escudo abstracto formado por el anillo.

**No usar:** cerebros, robots, nubes, logos de pfSense/Netgate, candados genéricos de stock.

### Variantes

| Variante | Uso |
|----------|-----|
| **Isotipo** | Solo el radar (favicon, avatar, ícono de pestaña) |
| **Logo horizontal** | Isotipo + “AI-NOC” + “Copilot” en una línea |
| **Logo apilado** | Isotipo arriba, texto abajo (cuadrado / splash) |
| **Monocromo claro** | Blanco / gris claro sobre fondo oscuro |
| **Monocromo oscuro** | Negro / gris oscuro sobre fondo claro |

### Especificación del isotipo (para SVG / CSS)

- Anillo exterior: stroke 2–2.5 px, radio ~40 % del canvas.
- Nodo central: círculo relleno, radio ~12 % del canvas.
- 2–3 arcos o puntos en el anillo (eventos), no simétricos perfectos (sensación de actividad).
- Sin degradados obligatorios en el MVP; un solo color de acento basta.
- Favicon: 32×32 y 16×16, isotipo simplificado (anillo + punto).

### Placeholder ASCII (README / terminal)
.--.
/    \     AI-NOC
|  •   |    Copilot
\    /
'--'

O una línea:
[ AI-NOC ] Copilot — logs de pfSense, 100 % local


### Implementación en Streamlit (sin assets)

Hasta tener SVG:

```python
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="🛰️",  # placeholder temporal; reemplazar por favicon propio
    layout="wide",
)
st.title("🛰️ AI-NOC Copilot")
st.caption("Copiloto local de logs de pfSense — 100 % offline")

## 4. Paleta de colores
Orientada a modo oscuro operativo (NOC / SOC), legible en Streamlit y en demos proyectadas.
Colores principales
Token,Hex,Uso
bg-deep,#0B1220,Fondo principal (casi negro azulado)
bg-panel,#111827,"Cards, expanders, sidebar"
bg-elevated,#1F2937,"Inputs, hovers suaves"
border,#374151,"Bordes, divisores"
text-primary,#F3F4F6,Texto principal
text-muted,#9CA3AF,"Captions, metadatos"
accent,#22D3EE,"Cian — acciones primarias, foco, links"
accent-dim,#0891B2,Hover / estado activo del acento

Severidad (obligatorio mantener coherencia)
Severidad,Token,Hex,Uso en UI
high,sev-high,#F43F5E,"Badge, borde izquierdo, métricas críticas"
medium,sev-medium,#F59E0B,"Badge, avisos"
low,sev-low,#34D399,"Badge, estado ok / bajo"

Estados auxiliares
Token,Hex,Uso
ok,#34D399,"Health OK, éxito de ingesta"
warn,#F59E0B,"Backend lento, umbral no alcanzado"
error,#F43F5E,Fallos de API / Ollama
info,#22D3EE,"Tips, captions informativos"

Modo claro (opcional, no prioritario)
Si hace falta exportar a PDF o slides claros:
Token,Hex
bg-light,#F8FAFC
text-on-light,#0F172A
accent,"#0891B2 (mismo cian, un tono más oscuro)"

El producto en runtime prioriza modo oscuro.
Contraste

Texto primario sobre bg-deep / bg-panel: ratio alto (gris muy claro).
No poner sev-high como fondo de bloques grandes de texto; usar badge o borde.
El acento cian no se usa para errores.

## 5. Tipografía

Rol,Familia,Notas
UI / títulos,"Inter, fallback system-ui, Segoe UI, sans-serif",Streamlit default es aceptable
Código / logs,"JetBrains Mono o ui-monospace, Consolas, monospace",st.code de logs filterlog
No usar,Fuentes display / script / Comic,Rompen tono NOC

tamaños orientativos:

Título página: grande, una sola línea “AI-NOC Copilot”
Subtítulos de sección: medium
Captions / timestamps: small + text-muted

## 6. Componentes UI (Streamlit)

Estructura de página

Header: título + caption (tagline).
Columna principal (izq.): eventos + filtros + paginación.
Columna lateral (der.): resumen, correlación, acciones de detección.
Expander superior: ingesta manual (secundario, no compite con el listado).

Badges de severidad
Formato de texto (sin CSS custom si no hace falta):
🔴 high   ·  🟠 medium   ·  🟢 low
O markdown:
**Severidad:** `high`
Si se inyecta CSS, preferir pastilla con fondo semitransparente del color de severidad y texto claro.

Botones
Tipo,Estilo Streamlit,Cuándo
Primario,"type=""primary""","Ingerir, correlacionar, acciones principales"
Secundario,default,"Anterior / Siguiente, filtros"
Peligro,no nativo — usar primary + copy claro,Evitar rojos en botones salvo confirmación real

Logs crudos
Siempre en st.code(..., language="text"), nunca como párrafo corrido. Fondo oscuro del tema ayuda a leer filterlog.
Estados vacíos

“No hay eventos con estos filtros.”
“No se detectaron patrones que superen el umbral.”

Sin ilustraciones stock.

## 7. CSS opcional para Streamlit

Inyectar solo si se quiere alinear colores sin theme completo. Ejemplo mínimo (air-gapped: sin CDNs ni fuentes remotas):

st.markdown(
    """
    <style>
    :root {
      --ainoc-bg: #0B1220;
      --ainoc-panel: #111827;
      --ainoc-elevated: #1F2937;
      --ainoc-border: #374151;
      --ainoc-accent: #22D3EE;
      --ainoc-accent-dim: #0891B2;
      --ainoc-text: #F3F4F6;
      --ainoc-muted: #9CA3AF;
      --ainoc-high: #F43F5E;
      --ainoc-medium: #F59E0B;
      --ainoc-low: #34D399;
    }
    .stApp { background: var(--ainoc-bg); color: var(--ainoc-text); }
    [data-testid="stSidebar"] { background: var(--ainoc-panel); }
    h1, h2, h3 { color: var(--ainoc-text) !important; }
    .ainoc-badge-high { color: var(--ainoc-high); font-weight: 600; }
    .ainoc-badge-medium { color: var(--ainoc-medium); font-weight: 600; }
    .ainoc-badge-low { color: var(--ainoc-low); font-weight: 600; }
    div[data-testid="stExpander"] {
      background: var(--ainoc-panel);
      border: 1px solid var(--ainoc-border);
      border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
Regla para agentes: no inventar más tokens; reutilizar esta tabla. No añadir dependencias de design systems en la nube ni CDNs externos (requisito air-gapped).

## 8. Copy de interfaz (español)

Lugar,Texto sugerido
Título,AI-NOC Copilot
Caption,Copiloto local de logs de pfSense — 100 % offline
Ingesta,Ingesta manual de logs
Placeholder paste,Aug 19 12:00:00 pfsense-prod filterlog: ...
Botón ingerir,Ingerir logs
Filtro búsqueda,Buscar en raw_message
Solo sin analizar,Solo sin analizar
Resumen,Resumen
Correlación,Correlacionar eventos sin analizar
Explicar,Explicar con IA
Paginación,Mostrando {start}–{end} de {total} · página {n}/{pages}

Evitar anglicismos innecesarios en botones (“Submit”, “Run AI”). “Explicar con IA” y “Correlacionar” ya están establecidos en el código.

## 9. README, demo y slides

README: título AI-NOC Copilot, tagline en la primera línea, badge opcional offline / air-gapped.
Demo grabada: fondo oscuro del dashboard; no cambiar tema a claro solo para la cámara.
Slides del curso: misma paleta (bg-deep, accent, severidades); un slide con el isotipo + tagline basta como portada de marca.

## 10. Checklist para agentes de código / diseño (frontend)

Al tocar UI o docs de producto:

 ¿El título visible sigue siendo AI-NOC Copilot?
 ¿El caption menciona offline / local / pfSense sin prometer nube?
 ¿Los colores de severidad respetan high=rose, medium=ámbar, low=esmeralda?
 ¿El acento interactivo es cian (#22D3EE), no el rojo de severidad?
 ¿No se añadieron CDNs, Google Fonts remotas ni assets externos?
 ¿Los logs siguen en st.code y el copy en español?
 ¿Favicon/page_icon es isotipo o el placeholder 🛰️ documentado aquí?
 ¿Filtros y paginación siguen usables en fondo oscuro (contraste de inputs)?
 ¿Estados vacíos usan el copy de esta guía, no mensajes genéricos en inglés?

Si un cambio de diseño contradice SPEC §3 (arquitectura) o el requisito air-gapped, decirlo explícitamente antes de implementarlo (SPEC §11).

## 11. Resumen ejecutivo (pegable en prompts de agentes)

Marca: AI-NOC Copilot
Tagline: Copiloto local de logs de pfSense — 100 % offline
Tono: técnico, calmado, sin hype
Isotipo: radar/anillo + nodo central (sin cerebro/nube/robot)
Paleta: bg #0B1220 / panel #111827 / elevated #1F2937 / border #374151
Texto: #F3F4F6 / muted #9CA3AF
Acento: #22D3EE (hover #0891B2)
Severidad: high #F43F5E · medium #F59E0B · low #34D399
UI: Streamlit wide, modo oscuro, logs en st.code, copy en español
Air-gapped: sin CDNs ni fuentes remotas
Estructura: header + col eventos/filtros | col resumen/correlación + expander ingesta

## 12. Mapa rápido token → Streamlit

Token,Dónde aplicarlo en el frontend
bg-deep,Fondo de .stApp
bg-panel,"Expanders, sidebar, “cards” visuales"
accent,"Links, foco, botones primary (vía theme o CSS)"
sev-high/medium/low,"Texto/badge junto a event[""severity""]"
text-muted,"st.caption, timestamps, “Mostrando X–Y de Z”"
mono,Solo st.code del raw_message

Última actualización: 20 ago 2026 — guía de branding para Fase 5 (dashboard) y entrega del curso.