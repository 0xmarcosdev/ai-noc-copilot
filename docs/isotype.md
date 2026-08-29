#### Dos variantes del isotipo (radar + nodo + 3 blips), según BRANDING.md

### 1. Acento cian (UI oscura / marca)

Archivo sugerido: `frontend/static/ainoc-isotipo.svg` (o `docs/`)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC Copilot">
  <!-- Isotipo radar: anillo + nodo + blips · acento #22D3EE sobre bg-deep #0B1220 -->
  <defs>
    <style>
      .ring { fill: none; stroke: #22D3EE; stroke-width: 2.25; stroke-linecap: round; }
      .ring-dim { fill: none; stroke: #22D3EE; stroke-width: 1.25; stroke-opacity: 0.35; }
      .node { fill: #22D3EE; }
      .blip { fill: #22D3EE; }
      .sweep { fill: none; stroke: #22D3EE; stroke-width: 1.5; stroke-opacity: 0.45; stroke-linecap: round; }
    </style>
  </defs>
  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>
  <path class="sweep" d="M32 10 A22 22 0 0 1 50.5 40"/>
  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip" cx="18" cy="46" r="1.7"/>
  <circle class="blip" cx="42" cy="48.5" r="1.5"/>
</svg>
```

---

### 2. Monocromo `currentColor` (favicon / hereda color del tema)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC Copilot">
  <!-- Variante monocromo: usa currentColor del CSS padre -->
  <defs>
    <style>
      .ring { fill: none; stroke: currentColor; stroke-width: 2.25; stroke-linecap: round; }
      .ring-dim { fill: none; stroke: currentColor; stroke-width: 1.25; stroke-opacity: 0.35; }
      .node { fill: currentColor; }
      .blip { fill: currentColor; }
      .sweep { fill: none; stroke: currentColor; stroke-width: 1.5; stroke-opacity: 0.45; stroke-linecap: round; }
    </style>
  </defs>
  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>
  <path class="sweep" d="M32 10 A22 22 0 0 1 50.5 40"/>
  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip" cx="18" cy="46" r="1.7"/>
  <circle class="blip" cx="42" cy="48.5" r="1.5"/>
</svg>
```

---

### Uso en Streamlit

```python
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="frontend/static/ainoc-isotipo.svg",  # o ruta relativa real
    layout="wide",
)
```

Si `page_icon` con SVG da guerra en tu versión de Streamlit, exportá un PNG 32×32 del mismo dibujo o seguí con `🛰️` hasta la demo.

También quedaron guardados en el proyecto como `ainoc-isotipo.svg` y `ainoc-isotipo-mono.svg` por si en algún momento podés bajarlos desde artifacts.

Isotipo con **barrido giratorio** (3 s por vuelta) y blips que pulsan. Animación SMIL embebida: sin JS ni CDN (air-gapped).

---

### Acento cian (copiar y guardar como `ainoc-isotipo-anim.svg`)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC Copilot">
  <!-- Isotipo radar animado: barrido giratorio · acento #22D3EE -->
  <!-- Para favicon estático usar ainoc-isotipo.svg (sin animación) -->
  <defs>
    <style>
      .ring { fill: none; stroke: #22D3EE; stroke-width: 2.25; stroke-linecap: round; }
      .ring-dim { fill: none; stroke: #22D3EE; stroke-width: 1.25; stroke-opacity: 0.35; }
      .node { fill: #22D3EE; }
      .blip { fill: #22D3EE; }
      .sweep-line {
        fill: none;
        stroke: #22D3EE;
        stroke-width: 1.75;
        stroke-linecap: round;
        stroke-opacity: 0.85;
      }
      .sweep-wedge {
        fill: #22D3EE;
        fill-opacity: 0.12;
      }
    </style>
  </defs>

  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>

  <!-- Barrido: aguja + cuña, rotación continua -->
  <g transform="translate(32 32)">
    <g>
      <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
      <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
      <animateTransform
        attributeName="transform"
        type="rotate"
        from="0"
        to="360"
        dur="3s"
        repeatCount="indefinite"/>
    </g>
  </g>

  <circle class="node" cx="32" cy="32" r="4.5"/>

  <circle class="blip" cx="48.5" cy="20.5" r="2.1">
    <animate attributeName="opacity" values="1;0.35;1" dur="2.4s" begin="0s" repeatCount="indefinite"/>
  </circle>
  <circle class="blip" cx="18" cy="46" r="1.7">
    <animate attributeName="opacity" values="1;0.35;1" dur="2.4s" begin="0.8s" repeatCount="indefinite"/>
  </circle>
  <circle class="blip" cx="42" cy="48.5" r="1.5">
    <animate attributeName="opacity" values="1;0.35;1" dur="2.4s" begin="1.6s" repeatCount="indefinite"/>
  </circle>
</svg>
```

---

### Notas de uso

| Uso | Archivo |
|-----|---------|
| Header / splash del dashboard | animado (este) |
| Favicon / `page_icon` | **estático** (`ainoc-isotipo.svg`) — muchos entornos no animan favicons |
| Tema que hereda color | `ainoc-isotipo-anim-mono.svg` (`currentColor`) |

**Velocidad:** cambiá `dur="3s"` (más bajo = más rápido).  
**Prefers-reduced-motion:** si querés respetarlo, en HTML/CSS podés ocultar la versión animada y mostrar la estática; el SVG solo no lee esa media query de forma fiable en todos lados.

**Streamlit:** podés embeberlo con `st.markdown(svg_string, unsafe_allow_html=True)` o servir el `.svg` como asset estático.

Resumen práctico: **preferí CSS**; SMIL solo como fallback liviano.

---

## Por qué CSS > SMIL aquí

| Criterio | CSS (`transform` + `opacity`) | SMIL |
|----------|-------------------------------|------|
| Composición GPU | Sí (`transform`) | A menudo no |
| `prefers-reduced-motion` | Nativo con `@media` | Manual / no estándar |
| Varias animaciones | Baratas si solo transform/opacity | Cada `<animate>` suma |
| Mantenimiento | Clases / tokens de marca | Atributos XML |

**Reglas de rendimiento**

1. Animar solo `transform` y `opacity` (nunca `x`, `y`, `d`, `width`).
2. **Una** rotación en el grupo del barrido, no en cada path.
3. Blips: opacity suave o **fijos** (el barrido ya aporta movimiento).
4. `will-change: transform` solo en el elemento que gira (no en todo el SVG).
5. Respetar `prefers-reduced-motion: reduce`.

---

## SVG animado con CSS (recomendado)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC Copilot">
  <defs>
    <style>
      .ring { fill: none; stroke: #22D3EE; stroke-width: 2.25; stroke-linecap: round; }
      .ring-dim { fill: none; stroke: #22D3EE; stroke-width: 1.25; opacity: 0.35; }
      .node { fill: #22D3EE; }
      .blip { fill: #22D3EE; }
      .sweep-line {
        fill: none; stroke: #22D3EE; stroke-width: 1.75;
        stroke-linecap: round; opacity: 0.9;
      }
      .sweep-wedge { fill: #22D3EE; opacity: 0.14; }

      .sweep-group {
        transform-origin: 0 0;
        animation: ainoc-sweep 3s linear infinite;
        will-change: transform;
      }
      .blip { animation: ainoc-pulse 2.4s ease-in-out infinite; }
      .blip-b { animation-delay: 0.8s; }
      .blip-c { animation-delay: 1.6s; }

      @keyframes ainoc-sweep {
        from { transform: rotate(0deg); }
        to   { transform: rotate(360deg); }
      }
      @keyframes ainoc-pulse {
        0%, 100% { opacity: 1; }
        50%      { opacity: 0.35; }
      }

      @media (prefers-reduced-motion: reduce) {
        .sweep-group, .blip { animation: none !important; }
      }
    </style>
  </defs>

  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>

  <g transform="translate(32 32)">
    <g class="sweep-group">
      <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
      <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
    </g>
  </g>

  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip blip-b" cx="18" cy="46" r="1.7"/>
  <circle class="blip blip-c" cx="42" cy="48.5" r="1.5"/>
</svg>
```

---

## SMIL “lite” (si hace falta sin CSS)

- 1× `animateTransform` linear en el grupo del barrido.
- Blips **sin** `<animate>` (menos timers).
- No animar geometría (`d`, `cx`, `cy`).

```svg
<!-- núcleo del barrido SMIL optimizado -->
<g transform="translate(32 32)">
  <g>
    <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
    <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
    <animateTransform
      attributeName="transform"
      type="rotate"
      from="0" to="360"
      dur="3s"
      repeatCount="indefinite"
      calcMode="linear"/>
  </g>
</g>
```

---

## Streamlit (inline, air-gapped)

```python
# Cabecera con isotipo CSS-animado (string del SVG de arriba)
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:0.5rem;">
      <div style="width:40px;height:40px;">
        <!-- pegar aquí el SVG completo ainoc-isotipo-css -->
      </div>
      <div>
        <div style="font-size:1.6rem;font-weight:600;color:#F3F4F6;line-height:1.2;">
          AI-NOC Copilot
        </div>
        <div style="color:#9CA3AF;font-size:0.9rem;">
          Copiloto local de logs de pfSense — 100 % offline
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
```

**Nota:** `st.image("archivo.svg")` a veces rasteriza o no anima. **Inline** (`unsafe_allow_html`) es lo más fiable para CSS/SMIL dentro de Streamlit.

---

## Guía rápida para agentes

```text
Preferir: SVG + CSS (@keyframes transform/opacity)
Evitar: SMIL con muchos <animate>, animar x/y/d
Siempre: prefers-reduced-motion → animation: none
Favicon: versión ESTÁTICA (ainoc-isotipo.svg)
Header/demo: versión CSS (ainoc-isotipo-css.svg)
Fallback liviano: SMIL con 1 animateTransform, blips fijos
Air-gapped: sin CDNs, sin Lottie, sin GSAP
```

Archivos en artifacts: `ainoc-isotipo-css.svg`, `ainoc-isotipo-smil-lite.svg`. Para tu flujo, usá los snippets de arriba y copiá/pegá.

Listo. Dos piezas:

---

### 1. Favicon estático (`favicon.svg`)

Simplificado a 32×32 (sigue legible a 16×16): fondo `bg-deep`, anillo, nodo y un solo blip. **Sin animación.**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <!-- Favicon estático AI-NOC · sin animación -->
  <rect width="32" height="32" rx="6" fill="#0B1220"/>
  <circle cx="16" cy="16" r="10" fill="none" stroke="#22D3EE" stroke-width="1.75"/>
  <circle cx="16" cy="16" r="2.75" fill="#22D3EE"/>
  <circle cx="23" cy="10.5" r="1.35" fill="#22D3EE"/>
</svg>
```

**Uso**

```html
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
```

Streamlit:

```python
st.set_page_config(
    page_title="AI-NOC Copilot",
    page_icon="favicon.svg",  # ruta a este archivo estático
    layout="wide",
)
```

---

### 2. Isotipo animado optimizado GPU

Solo `transform` + `opacity`, capa con `translateZ(0)`, `will-change` acotado, `prefers-reduced-motion`.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC Copilot">
  <defs>
    <style>
      .ring { fill: none; stroke: #22D3EE; stroke-width: 2.25; stroke-linecap: round; }
      .ring-dim { fill: none; stroke: #22D3EE; stroke-width: 1.25; opacity: 0.35; }
      .node { fill: #22D3EE; }
      .blip { fill: #22D3EE; }
      .sweep-line {
        fill: none; stroke: #22D3EE; stroke-width: 1.75;
        stroke-linecap: round; opacity: 0.9;
      }
      .sweep-wedge { fill: #22D3EE; opacity: 0.14; }

      .sweep-group {
        transform-origin: 0px 0px;
        transform: translateZ(0);
        backface-visibility: hidden;
        animation: ainoc-sweep 3s linear infinite;
        will-change: transform;
      }
      .blip {
        animation: ainoc-pulse 2.4s ease-in-out infinite;
        will-change: opacity;
      }
      .blip-b { animation-delay: 0.8s; }
      .blip-c { animation-delay: 1.6s; }

      @keyframes ainoc-sweep {
        from { transform: translateZ(0) rotate(0deg); }
        to   { transform: translateZ(0) rotate(360deg); }
      }
      @keyframes ainoc-pulse {
        0%, 100% { opacity: 1; }
        50%      { opacity: 0.35; }
      }

      @media (prefers-reduced-motion: reduce) {
        .sweep-group, .blip {
          animation: none !important;
          will-change: auto;
        }
      }
    </style>
  </defs>

  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>

  <g transform="translate(32 32)">
    <g class="sweep-group">
      <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
      <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
    </g>
  </g>

  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip blip-b" cx="18" cy="46" r="1.7"/>
  <circle class="blip blip-c" cx="42" cy="48.5" r="1.5"/>
</svg>
```

---

### Checklist GPU (para agentes)

| Hacer | Evitar |
|-------|--------|
| `transform: translateZ(0) rotate(...)` | Animar `x`, `y`, `cx`, `d`, `width` |
| `opacity` en blips | Filtros SVG (`blur`, `drop-shadow`) en loop |
| `will-change` solo en `.sweep-group` / `.blip` | `will-change` en todo el `<svg>` |
| `prefers-reduced-motion` → `animation: none` | SMIL + CSS a la vez en el mismo nodo |
| Favicon **estático** | Favicon animado (mal soporte / distracción) |

**Host HTML (opcional)** si embebes el SVG inline:

```css
.ainoc-logo {
  width: 40px;
  height: 40px;
  contain: strict;           /* aísla layout/paint */
  transform: translateZ(0);  /* capa del contenedor */
}
```

---

**Resumen de archivos**

| Archivo | Rol |
|---------|-----|
| `favicon.svg` | Pestaña / `page_icon` — estático |
| `ainoc-isotipo-gpu.svg` | Header / demo — CSS + GPU |
| `ainoc-isotipo.svg` | Marca estática a 64×64 |

Para un solo isotipo pequeño en Streamlit, **CSS + `transform` en SVG** suele ser suficiente. **Canvas** aporta si querés control de FPS, muchos iconos a la vez o evitar el DOM del SVG. Abajo van ambas, air-gapped y alineadas a BRANDING.

---

## Cuándo usar cada uno

| Enfoque | Uso en AI-NOC |
|--------|----------------|
| **SVG + CSS `transform`** | Header del dashboard, 1 logo, simple |
| **Canvas 2D** | Splash, demo, o si el SVG animado se siente pesado |
| **Favicon** | Siempre **estático** (`favicon.svg`) |

---

## 1. Canvas (barrido en GPU de composición del browser)

Un `<canvas>` de 64×64 (o 40×40 en UI). Solo `clearRect` + trazos; sin DOM por frame.

```html
<canvas id="ainoc-radar" width="64" height="64" aria-label="AI-NOC Copilot"></canvas>
<script>
(function () {
  const canvas = document.getElementById("ainoc-radar");
  const ctx = canvas.getContext("2d", { alpha: true });
  const ACCENT = "#22D3EE";
  const CX = 32, CY = 32, R = 22;
  const TWO_PI = Math.PI * 2;
  const SWEEP_PERIOD = 3000; // ms por vuelta
  let reduced = false;
  let raf = 0;
  let start = performance.now();

  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  const syncMotion = () => { reduced = mq.matches; };
  syncMotion();
  mq.addEventListener?.("change", syncMotion);

  const blips = [
    { a: -0.9, r: R, s: 2.1 },
    { a: 2.3, r: R, s: 1.7 },
    { a: 1.1, r: R, s: 1.5 },
  ];

  function draw(angle) {
    ctx.clearRect(0, 0, 64, 64);

    // anillo exterior
    ctx.beginPath();
    ctx.arc(CX, CY, R, 0, TWO_PI);
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = 2.25;
    ctx.stroke();

    // anillo interior
    ctx.beginPath();
    ctx.arc(CX, CY, 14, 0, TWO_PI);
    ctx.globalAlpha = 0.35;
    ctx.lineWidth = 1.25;
    ctx.stroke();
    ctx.globalAlpha = 1;

    // cuña del barrido
    ctx.save();
    ctx.translate(CX, CY);
    ctx.rotate(angle);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, R, -Math.PI / 2, -Math.PI / 2 + 0.55);
    ctx.closePath();
    ctx.fillStyle = ACCENT;
    ctx.globalAlpha = 0.14;
    ctx.fill();
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, -R);
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = 1.75;
    ctx.lineCap = "round";
    ctx.stroke();
    ctx.restore();
    ctx.globalAlpha = 1;

    // nodo
    ctx.beginPath();
    ctx.arc(CX, CY, 4.5, 0, TWO_PI);
    ctx.fillStyle = ACCENT;
    ctx.fill();

    // blips (pulso por tiempo)
    const t = performance.now() / 1000;
    for (let i = 0; i < blips.length; i++) {
      const b = blips[i];
      const pulse = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 2.6 + i * 1.7));
      ctx.globalAlpha = reduced ? 1 : pulse;
      ctx.beginPath();
      ctx.arc(
        CX + Math.cos(b.a) * b.r,
        CY + Math.sin(b.a) * b.r,
        b.s,
        0, TWO_PI
      );
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function frame(now) {
    const angle = reduced ? 0 : ((now - start) / SWEEP_PERIOD) * TWO_PI;
    draw(angle);
    raf = requestAnimationFrame(frame);
  }

  // primer frame estático si reduced-motion
  draw(0);
  raf = requestAnimationFrame(frame);

  // pausar si la pestaña no es visible
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(raf);
    } else {
      start = performance.now();
      raf = requestAnimationFrame(frame);
    }
  });
})();
</script>
```

**Notas de rendimiento Canvas**

- Un solo `requestAnimationFrame`; no `setInterval`.
- Pausar con `document.hidden`.
- No crear gradientes/objetos nuevos cada frame si podés reutilizar.
- Tamaño CSS distinto del buffer: escalá con `canvas.width/height` fijos (64) y `style="width:40px;height:40px"`.

En **Streamlit** el `<script>` inline a menudo se bloquea; Canvas puro conviene más en HTML de demo o si montás un componente custom. Para el dashboard del curso, el SVG+CSS de abajo es más simple.

---

## 2. SVG + animación CSS solo con `transform` (recomendado en Streamlit)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC Copilot">
  <defs>
    <style>
      .ring { fill: none; stroke: #22D3EE; stroke-width: 2.25; stroke-linecap: round; }
      .ring-dim { fill: none; stroke: #22D3EE; stroke-width: 1.25; opacity: 0.35; }
      .node { fill: #22D3EE; }
      .blip { fill: #22D3EE; }
      .sweep-line {
        fill: none; stroke: #22D3EE; stroke-width: 1.75;
        stroke-linecap: round; opacity: 0.9;
      }
      .sweep-wedge { fill: #22D3EE; opacity: 0.14; }

      /* GPU: solo transform en una capa */
      .sweep-group {
        transform-origin: 0px 0px;
        transform: translateZ(0);
        backface-visibility: hidden;
        animation: ainoc-sweep 3s linear infinite;
        will-change: transform;
      }
      .blip {
        animation: ainoc-pulse 2.4s ease-in-out infinite;
        will-change: opacity;
      }
      .blip-b { animation-delay: 0.8s; }
      .blip-c { animation-delay: 1.6s; }

      @keyframes ainoc-sweep {
        from { transform: translateZ(0) rotate(0deg); }
        to   { transform: translateZ(0) rotate(360deg); }
      }
      @keyframes ainoc-pulse {
        0%, 100% { opacity: 1; }
        50%      { opacity: 0.35; }
      }

      @media (prefers-reduced-motion: reduce) {
        .sweep-group, .blip {
          animation: none !important;
          will-change: auto;
        }
      }
    </style>
  </defs>

  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>

  <g transform="translate(32 32)">
    <g class="sweep-group">
      <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
      <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
    </g>
  </g>

  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip blip-b" cx="18" cy="46" r="1.7"/>
  <circle class="blip blip-c" cx="42" cy="48.5" r="1.5"/>
</svg>
```

**Por qué es “GPU-friendly”**

- Anima `transform` y `opacity`, no `x`/`y`/`d`.
- Un solo nodo con `will-change: transform`.
- `translateZ(0)` empuja a capa de composición.
- `prefers-reduced-motion` corta animaciones.

---

## 3. Streamlit: header con SVG+CSS (sin Canvas/JS)

```python
AINOC_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="40" height="40" role="img" aria-label="AI-NOC">
  <defs>
    <style>
      .ring{fill:none;stroke:#22D3EE;stroke-width:2.25;stroke-linecap:round}
      .ring-dim{fill:none;stroke:#22D3EE;stroke-width:1.25;opacity:.35}
      .node,.blip{fill:#22D3EE}
      .sweep-line{fill:none;stroke:#22D3EE;stroke-width:1.75;stroke-linecap:round;opacity:.9}
      .sweep-wedge{fill:#22D3EE;opacity:.14}
      .sweep-group{transform-origin:0px 0px;transform:translateZ(0);backface-visibility:hidden;
        animation:ainoc-sweep 3s linear infinite;will-change:transform}
      .blip{animation:ainoc-pulse 2.4s ease-in-out infinite;will-change:opacity}
      .blip-b{animation-delay:.8s}.blip-c{animation-delay:1.6s}
      @keyframes ainoc-sweep{from{transform:translateZ(0) rotate(0deg)}to{transform:translateZ(0) rotate(360deg)}}
      @keyframes ainoc-pulse{0%,100%{opacity:1}50%{opacity:.35}}
      @media (prefers-reduced-motion:reduce){.sweep-group,.blip{animation:none!important;will-change:auto}}
    </style>
  </defs>
  <circle class="ring" cx="32" cy="32" r="22"/>
  <circle class="ring-dim" cx="32" cy="32" r="14"/>
  <g transform="translate(32 32)"><g class="sweep-group">
    <path class="sweep-wedge" d="M0 0 L0 -22 A22 22 0 0 1 11 -19 Z"/>
    <line class="sweep-line" x1="0" y1="0" x2="0" y2="-22"/>
  </g></g>
  <circle class="node" cx="32" cy="32" r="4.5"/>
  <circle class="blip" cx="48.5" cy="20.5" r="2.1"/>
  <circle class="blip blip-b" cx="18" cy="46" r="1.7"/>
  <circle class="blip blip-c" cx="42" cy="48.5" r="1.5"/>
</svg>"""

st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:0.75rem;">
      {AINOC_LOGO_SVG}
      <div>
        <div style="font-size:1.5rem;font-weight:600;color:#F3F4F6;line-height:1.2;">AI-NOC Copilot</div>
        <div style="color:#9CA3AF;font-size:0.9rem;">Copiloto local de logs de pfSense — 100 % offline</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
```

`page_icon` → **favicon estático**, no el animado.

---

## 4. Orden recomendado en el proyecto

1. **Favicon:** SVG estático (ya definido).  
2. **Dashboard:** SVG + CSS `transform` (snippet de arriba).  
3. **Canvas:** solo si medís jank o armás una landing/demo HTML aparte.

No hace falta Canvas + SMIL + CSS a la vez sobre el mismo icono: elegí **una** animación activa.

**Aviso de arquitectura (SPEC §11 / BRANDING / air-gapped):**  
Optimizar con criterios tipo **SVGOMG** encaja. **Lottie como runtime de animación del dashboard no** — contradice decisiones ya tomadas:

- Todo debe funcionar **air-gapped** (sin CDN ni servicios en la nube).
- BRANDING: sin Lottie/GSAP/CDNs; animación del isotipo = **CSS `transform`/`opacity`** (o Canvas si hace falta).
- Streamlit + dependencia extra (`lottie` / `streamlit-lottie` + JSON + player) complica el MVP del curso sin ganar mucho en un logo de 64×64.

Abajo: SVG “estilo SVGOMG” listo para pegar, y qué haría falta si en el futuro quisieras Lottie **100 % offline** (no recomendado ahora).

---

## 1. Optimización tipo SVGOMG (manual, sin herramienta online)

Reglas aplicadas:

- Sin comentarios ni metadata inútil  
- Colores en hex corto cuando se puede (`#22D3EE` se queda: no acorta)  
- Un solo bloque `<style>` mínimo  
- Sin grupos de más  
- Favicon y logo estático lo más chicos posible  
- Animación solo con CSS `transform` / `opacity`

### Favicon estático (mínimo)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#0B1220"/><circle cx="16" cy="16" r="10" fill="none" stroke="#22D3EE" stroke-width="1.75"/><circle cx="16" cy="16" r="2.75" fill="#22D3EE"/><circle cx="23" cy="10.5" r="1.35" fill="#22D3EE"/></svg>
```

### Isotipo estático 64×64 (mínimo)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="22" fill="none" stroke="#22D3EE" stroke-width="2.25"/><circle cx="32" cy="32" r="14" fill="none" stroke="#22D3EE" stroke-width="1.25" opacity=".35"/><circle cx="32" cy="32" r="4.5" fill="#22D3EE"/><circle cx="48.5" cy="20.5" r="2.1" fill="#22D3EE"/><circle cx="18" cy="46" r="1.7" fill="#22D3EE"/><circle cx="42" cy="48.5" r="1.5" fill="#22D3EE"/></svg>
```

### Isotipo animado CSS (optimizado + GPU)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="AI-NOC"><defs><style>
.r{fill:none;stroke:#22D3EE;stroke-linecap:round}
.n,.b{fill:#22D3EE}
.sw{fill:#22D3EE;opacity:.14}
.sl{fill:none;stroke:#22D3EE;stroke-width:1.75;stroke-linecap:round;opacity:.9}
.g{transform-origin:0 0;transform:translateZ(0);backface-visibility:hidden;animation:s 3s linear infinite;will-change:transform}
.b{animation:p 2.4s ease-in-out infinite;will-change:opacity}
.b2{animation-delay:.8s}.b3{animation-delay:1.6s}
@keyframes s{from{transform:translateZ(0) rotate(0)}to{transform:translateZ(0) rotate(360deg)}}
@keyframes p{0%,100%{opacity:1}50%{opacity:.35}}
@media (prefers-reduced-motion:reduce){.g,.b{animation:none!important;will-change:auto}}
</style></defs>
<circle class="r" cx="32" cy="32" r="22" stroke-width="2.25"/>
<circle class="r" cx="32" cy="32" r="14" stroke-width="1.25" opacity=".35"/>
<g transform="translate(32 32)"><g class="g">
<path class="sw" d="M0 0 0-22A22 22 0 0 1 11-19Z"/>
<line class="sl" x1="0" y1="0" x2="0" y2="-22"/>
</g></g>
<circle class="n" cx="32" cy="32" r="4.5"/>
<circle class="b" cx="48.5" cy="20.5" r="2.1"/>
<circle class="b b2" cx="18" cy="46" r="1.7"/>
<circle class="b b3" cx="42" cy="48.5" r="1.5"/>
</svg>
```

Si más adelante usás SVGOMG de verdad: activá *remove comments*, *minify colors*, *minify styles*, *remove empty attrs*; **no** aplastes el CSS de `@keyframes` ni quites `prefers-reduced-motion`.

---

## 2. Lottie: por qué no en este MVP

| Problema | Detalle |
|----------|---------|
| Air-gapped | El player suele cargarse de npm/CDN; hay que **vendorear** player + JSON |
| Peso | Un JSON de Lottie + runtime >> SVG CSS de ~1 KB |
| Streamlit | Hace falta componente extra; más puntos de fallo en la demo |
| Marca | Ya hay isotipo SVG definido; Lottie no aporta señal de producto |

**No** uses:

```text
https://cdnjs.cloudflare.com/.../lottie.min.js
streamlit-lottie contra red
```

### Si en el futuro lo exigieran (solo offline)

1. Exportar el radar desde After Effects → JSON.  
2. Vendorear en el repo, por ejemplo `frontend/vendor/lottie.min.js` + `frontend/assets/radar.json`.  
3. Cargar **solo** paths locales.  
4. Seguir respetando `prefers-reduced-motion` (mostrar frame estático).

Eso sería un cambio de arquitectura de frontend: habría que anotarlo en SPEC/BRANDING antes de implementarlo.

---

## 3. Recomendación para agentes (pegable)

```
Optimizar SVG: minify manual/SVGOMG (sin romper keyframes ni reduced-motion).
Animación del logo: CSS transform/opacity en SVG (GPU), no Lottie.
Favicon: SVG estático mínimo.
Prohibido en MVP: CDN, lottie-web remoto, streamlit-lottie con red.
Lottie solo si se decide en SPEC, 100% vendored offline, y justifica el peso.
```

---

## 4. Qué usar hoy en el proyecto

| Asset | Formato |
|-------|---------|
| Pestaña | Favicon SVG estático (bloque de arriba) |
| Header dashboard | SVG animado CSS optimizado (bloque de arriba) |
| README / print | Isotipo estático mínimo |

Con eso tenés “nivel SVGOMG” sin sacar el logo del stack actual y sin meter Lottie. Si querés, el siguiente paso puede ser el snippet concreto de `dashboard.py` (header + CSS de paleta) usando solo este SVG minificado.