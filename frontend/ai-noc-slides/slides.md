---
theme: default
title: AI-NOC Copilot
info: |
  AI-NOC Copilot
  IA Estratégica: El Programador Aumentado
  Marcos Ruíz
class: noc-deck
highlighter: shiki
lineNumbers: false
fonts:
  sans: Inter
  serif: Inter
  mono: JetBrains Mono
transition: slide-left
mdc: true
---

<!-- SLIDE 01 · PORTADA -->
<div class="cover-slide">
  <div class="cover-top">
    <span class="status-dot"></span>
    <span>PROYECTO FINAL · IA ESTRATÉGICA</span>
  </div>
  <div class="cover-main">
    <div class="project-mark">
      <img class="ainoc-isotipo" src="/assets/icons/diagram_animated.svg" alt="AI-NOC Copilot" />
    </div>
    <div class="cover-copy">
      <div class="eyebrow accent-green">01 · PROYECTO FINAL</div>
      <h1 class="cover-title">AI-NOC<br><span>Copilot</span></h1>
      <p class="cover-subtitle">Un copiloto de red <strong>100% local</strong> para convertir eventos de infraestructura en decisiones operativas explicables.</p>
      <div class="acronym-row">
        <div class="acronym-card"><strong>AI</strong><span>Artificial Intelligence</span></div>
        <div class="acronym-card"><strong>NOC</strong><span>Network Operations Center</span></div>
      </div>
    </div>
  </div>
  <div class="cover-bottom">
    <div><div class="meta-label">AUTOR</div><div class="meta-value">Marcos Ruíz</div></div>
    <div><div class="meta-label">CURSO</div><div class="meta-value">IA Estratégica: El Programador Aumentado</div></div>
    <div><div class="meta-label">FECHA</div><div class="meta-value">2026</div></div>
    <div class="repo-pill"><span>⌁</span> github.com/0xmarcosdev/ai-noc-copilot</div>
  </div>
</div>

---
zoom: 0.85
---

<!-- SLIDE 02 · EL PROBLEMA -->
<div class="slide-shell">
  <div class="slide-heading">
    <div class="eyebrow">02 · EL PROBLEMA</div>
    <h2>¿Cómo llevamos IA a una red que <span>no puede hablar con Internet?</span></h2>
  </div>
  <div class="problem-layout">
    <div class="problem-left">
      <div class="section-kicker"><span class="kicker-line"></span>EL CONTEXTO OPERATIVO</div>
      <div class="network-visual">
        <div class="hq-node"><div class="node-icon">NOC</div><strong>Dirección territorial</strong><small>Recepción · análisis · respuesta</small></div>
        <div class="spoke spoke-1"><span>SUCURSAL 01</span></div>
        <div class="spoke spoke-2"><span>SUCURSAL 02</span></div>
        <div class="spoke spoke-3"><span>SUCURSAL 03</span></div>
        <div class="spoke spoke-4"><span>… múltiples sucursales</span></div>
      </div>
      <p class="visual-caption">Arquitectura <strong>hub-and-spoke</strong>: muchos cortafuegos pfSense convergen en una sede central.</p>
    </div>
    <div class="problem-right">
      <div v-click class="problem-card danger-card">
        <div class="card-symbol">01</div>
        <div><h3>Una frontera de seguridad</h3><p>La red corporativa opera <strong>sin acceso a Internet</strong> por políticas de seguridad.</p></div>
      </div>
      <div v-click class="problem-card blue-card">
        <div class="card-symbol">02</div>
        <div><h3>Muchos puntos de observación</h3><p>Cada sucursal genera eventos. La sede central termina recibiendo el ruido de toda la infraestructura.</p></div>
      </div>
      <div v-click class="problem-card yellow-card">
        <div class="card-symbol">03</div>
        <div><h3>El volumen oculta el patrón</h3><p>Un evento aislado puede parecer irrelevante. Varios eventos relacionados pueden contar una historia completamente distinta.</p></div>
      </div>
      <div class="problem-bottom">
        <span class="problem-arrow">→</span>
        <strong>Desafío:</strong> llevar capacidad de IA al entorno aislado <span class="highlight-green">sin sacar los datos de la red.</span>
      </div>
    </div>
  </div>
</div>

---
zoom: 0.91
---

<!-- SLIDE 03 · OBJETIVO -->
<div class="slide-shell">
  <div class="slide-heading">
    <div class="eyebrow">03 · EL OBJETIVO</div>
    <h2>Un copiloto que <span>observa, correlaciona y explica</span></h2>
  </div>
  <div class="objective-layout">
    <div class="objective-intro">
      <div class="objective-badge"><span class="badge-dot"></span>AI-NOC</div>
      <h3>No reemplaza al administrador. <span>Le quita ruido.</span></h3>
      <p>La aplicación convierte logs de firewall en información operativa estructurada, manteniendo la clasificación de seguridad fuera del LLM.</p>
      <div class="objective-equation">
        <span>LOGS</span> <b>→</b> <span>HEURÍSTICA</span> <b>→</b> <span>CONTEXTO</span> <b>→</b> <span>EXPLICACIÓN</span>
      </div>
    </div>
    <div class="objective-list">
      <div v-click class="objective-item"><div class="objective-number">01</div><div><h3>Ingerir</h3><p>Recibir y normalizar logs provenientes de pfSense.</p></div></div>
      <div v-click class="objective-item"><div class="objective-number">02</div><div><h3>Persistir</h3><p>Guardar los eventos en SQLite para consulta y análisis.</p></div></div>
      <div v-click class="objective-item"><div class="objective-number">03</div><div><h3>Detectar</h3><p>Aplicar regex, entropía y estadística de forma determinista.</p></div></div>
      <div v-click class="objective-item"><div class="objective-number">04</div><div><h3>Correlacionar</h3><p>Relacionar eventos para encontrar patrones que un evento aislado oculta.</p></div></div>
      <div v-click class="objective-item"><div class="objective-number">05</div><div><h3>Explicar</h3><p>Usar un LLM local para traducir el resultado a lenguaje natural.</p></div></div>
    </div>
  </div>
</div>

---
zoom: 0.87
---

<!-- SLIDE 04 · ARQUITECTURA -->
<div class="slide-shell architecture-slide">
  <div class="slide-heading compact-heading">
    <div class="eyebrow">04 · ARQUITECTURA GENERAL</div>
    <h2>Del <span>log bruto</span> a una explicación accionable</h2>
  </div>
  <div class="diagram-card architecture-card">
    <img src="./diagrams/arquitectura.svg" alt="Arquitectura general de AI-NOC Copilot" />
  </div>
  <div class="architecture-caption">
    <div v-click class="architecture-step"><span class="step-dot green"></span><strong>Entrada</strong><span>logs pfSense</span></div>
    <div class="flow-arrow">→</div>
    <div v-click class="architecture-step"><span class="step-dot blue"></span><strong>Ingesta</strong><span>parseo + SQLite</span></div>
    <div class="flow-arrow">→</div>
    <div v-click class="architecture-step"><span class="step-dot red"></span><strong>Detección</strong><span>heurísticas</span></div>
    <div class="flow-arrow">→</div>
    <div v-click class="architecture-step"><span class="step-dot yellow"></span><strong>Correlación</strong><span>contexto temporal</span></div>
    <div class="flow-arrow">→</div>
    <div v-click class="architecture-step"><span class="step-dot purple"></span><strong>LLM local</strong><span>explicación</span></div>
  </div>
  <div class="architecture-footer">
    <span class="footer-lock">●</span>
    <strong>Todo permanece dentro de la red corporativa.</strong>
    <span>Sin API externa · sin nube · sin transferencia de logs.</span>
  </div>
</div>

---
zoom: 0.88
---

<!-- SLIDE 05 · DECISIONES DE DISEÑO -->
<div class="slide-shell">
  <div class="slide-heading">
    <div class="eyebrow">05 · DECISIONES DE DISEÑO</div>
    <h2>Diseñar para el entorno real, no para el <span>caso ideal</span></h2>
  </div>
  <div class="design-grid">
    <div v-click class="design-card green-accent">
      <div class="design-number">01</div>
      <div class="design-content">
        <span class="design-tag">DECISIÓN</span>
        <h3>Clasificación determinista</h3>
        <p>La seguridad no depende de una respuesta probabilística. Regex, entropía y estadística producen el veredicto.</p>
        <div class="tradeoff"><strong>Trade-off</strong> Menos flexibilidad semántica, mucha más trazabilidad.</div>
        <div class="impact">→ Resultado: comportamiento reproducible.</div>
      </div>
    </div>
    <div v-click class="design-card blue-accent">
      <div class="design-number">02</div>
      <div class="design-content">
        <span class="design-tag">DECISIÓN</span>
        <h3>LLM local como capa de explicación</h3>
        <p>Ollama + modelo local reciben únicamente el contexto que ya fue producido por el motor determinista.</p>
        <div class="tradeoff"><strong>Trade-off</strong> Menor capacidad que un modelo cloud, pero cero dependencia externa.</div>
        <div class="impact">→ Resultado: IA útil dentro del air-gap.</div>
      </div>
    </div>
    <div v-click class="design-card purple-accent">
      <div class="design-number">03</div>
      <div class="design-content">
        <span class="design-tag">DECISIÓN</span>
        <h3>Ollama nativo en el host</h3>
        <p>El runtime del modelo corre directamente sobre el sistema, evitando una capa de virtualización innecesaria.</p>
        <div class="tradeoff"><strong>Trade-off</strong> Menos aislamiento, pero acceso más directo a CPU/RAM/GPU.</div>
        <div class="impact">→ Resultado: despliegue local más simple.</div>
      </div>
    </div>
    <div v-click class="design-card yellow-accent">
      <div class="design-number">04</div>
      <div class="design-content">
        <span class="design-tag">DECISIÓN</span>
        <h3>SQLite + Streamlit para el MVP</h3>
        <p>Se priorizó una arquitectura pequeña, auditable y fácil de desplegar en una infraestructura sin Internet.</p>
        <div class="tradeoff"><strong>Trade-off</strong> Menor escalabilidad que una plataforma distribuida.</div>
        <div class="impact">→ Resultado: MVP operativo con baja complejidad.</div>
      </div>
    </div>
  </div>
  <div class="design-summary">
    <span>La pregunta no fue</span> <strong>“¿qué tecnología es más potente?”</strong> <span>sino</span> <strong>“¿qué arquitectura funciona aquí?”</strong>
  </div>
</div>

---
zoom: 0.88
---

<!-- SLIDE 06 · DETERMINISMO + LLM -->
<div class="slide-shell deterministic-slide">
  <div class="slide-heading compact-heading">
    <div class="eyebrow">06 · PRINCIPIO NO NEGOCIABLE</div>
    <h2>La IA <span>no decide</span> qué ocurrió</h2>
  </div>
  <div class="deterministic-diagram-wrap">
    <div class="diagram-card deterministic-card">
      <img src="./diagrams/determinismo-vs-llm.svg" alt="Flujo de determinismo y LLM" />
    </div>
  </div>
  <div class="deterministic-cards">
    <div v-click class="logic-card logic-green">
      <div class="logic-icon">01</div>
      <div><span>HEURÍSTICA</span><h3>Decide QUÉ pasó</h3><p>Identifica patrones, calcula señales y asigna la clasificación de seguridad.</p></div>
    </div>
    <div v-click class="logic-card logic-purple">
      <div class="logic-icon">02</div>
      <div><span>LLM LOCAL</span><h3>Explica CÓMO comunicarlo</h3><p>Convierte el resultado estructurado en una explicación útil para el operador.</p></div>
    </div>
    <div v-click class="logic-card logic-red">
      <div class="logic-icon">03</div>
      <div><span>GUARDRAIL</span><h3>El modelo no puede cambiar el veredicto</h3><p>Si el LLM falla, la detección continúa siendo válida.</p></div>
    </div>
  </div>
</div>

---
zoom: 0.85
---

<!-- SLIDE 07 · CORRELACIÓN -->
<div class="slide-shell">
  <div class="slide-heading compact-heading">
    <div class="eyebrow">07 · CORRELACIÓN</div>
    <h2>Un evento puede ser ruido.</h2>
    <p class="corr-sub">El patrón cuenta una historia.</p>
  </div>
  <div class="correlation-layout correlation-tall">
    <div class="correlation-copy">
      <div class="comparison-label">ANTES</div>
      <div v-click class="event-box low">
        <div class="event-severity">LOW</div>
        <div><strong>Evento aislado</strong><p>Un intento de conexión sospechoso. Sin suficiente contexto para elevar la prioridad.</p></div>
      </div>
      <div class="correlation-divider"><span>+</span><span>+</span><span>+</span></div>
      <div class="comparison-label high-label">DESPUÉS</div>
      <div v-click class="event-box high">
        <div class="event-severity">HIGH</div>
        <div><strong>Eventos correlacionados</strong><p>Múltiples señales relacionadas en tiempo, origen, destino o comportamiento.</p></div>
      </div>
      <div v-click class="correlation-result">
        <span class="result-arrow">↗</span>
        <div><strong>La severidad cambia porque cambia el contexto.</strong><p>No porque el LLM “opine”, sino porque el motor encontró evidencia adicional.</p></div>
      </div>
    </div>
    <div class="correlation-visual">
      <div class="diagram-card correlation-card correlation-card-tall">
        <img src="./diagrams/correlacion.svg" alt="Correlación de eventos" />
      </div>
    </div>
  </div>
</div>

---
zoom: 0.85
---

<!-- SLIDE 08 · DEMO -->
<div class="slide-shell demo-slide">
  <div class="slide-heading">
    <div class="eyebrow">08 · DEMO EN VIVO</div>
    <h2>Del log al <span>diagnóstico explicado</span></h2>
  </div>
  <div class="demo-layout">
    <div class="demo-screen">
      <div class="terminal-bar">
        <span></span><span></span><span></span>
        <label>AI-NOC COPILOT / LIVE</label>
      </div>
      <div class="terminal-content">
        <div class="terminal-line muted">$ ainoc analyze --source pfsense</div>
        <div class="terminal-line"><span class="t-green">✓</span> 128 eventos ingeridos</div>
        <div class="terminal-line"><span class="t-green">✓</span> 17 patrones detectados</div>
        <div class="terminal-line"><span class="t-yellow">!</span> 4 eventos correlacionados</div>
        <div class="terminal-line"><span class="t-red">!</span> 1 patrón elevado a HIGH</div>
        <div class="terminal-line"><span class="t-purple">AI</span> generando explicación local...</div>
        <div class="terminal-result">
          <span>SEVERITY</span>
          <strong>HIGH</strong>
          <p>Múltiples eventos relacionados sugieren un patrón de actividad coordinada. Revisar origen y frecuencia.</p>
        </div>
      </div>
    </div>
    <div class="demo-timeline">
      <div v-click class="demo-step"><div class="demo-index">01</div><div><span>INGESTA</span><h3>Cargar logs pfSense</h3><p>El sistema recibe eventos reales o sintéticos.</p></div></div>
      <div class="demo-connector"></div>
      <div v-click class="demo-step"><div class="demo-index">02</div><div><span>ANÁLISIS</span><h3>Ejecutar heurísticas</h3><p>Regex, entropía y señales estadísticas.</p></div></div>
      <div class="demo-connector"></div>
      <div v-click class="demo-step"><div class="demo-index">03</div><div><span>CORRELACIÓN</span><h3>Construir contexto</h3><p>Relacionar eventos del mismo patrón.</p></div></div>
      <div class="demo-connector"></div>
      <div v-click class="demo-step"><div class="demo-index">04</div><div><span>EXPLICACIÓN</span><h3>Consultar el LLM local</h3><p>Ollama transforma el resultado en lenguaje natural.</p></div></div>
      <div class="demo-connector"></div>
      <div v-click class="demo-step"><div class="demo-index">05</div><div><span>DASHBOARD</span><h3>Mostrar el resultado</h3><p>Evidencia + contexto + explicación.</p></div></div>
    </div>
  </div>
  <div class="demo-footer">
    <span class="live-dot"></span>
    <strong>La demo muestra el flujo completo, no una maqueta.</strong>
    <span>Entrada → detección → correlación → explicación → dashboard</span>
  </div>
</div>

---
zoom: 0.95
---

<!-- SLIDE 09 · STACK + CALIDAD -->
<div class="slide-shell">
  <div class="slide-heading compact-heading">
    <div class="eyebrow">09 · STACK Y CALIDAD</div>
    <h2>Un MVP pequeño, <span>medible y reproducible</span></h2>
  </div>
  <div class="stack-layout">
    <div class="stack-column">
      <div class="stack-section-title">CAPA DE APLICACIÓN</div>
      <div class="stack-grid">
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/python.svg" alt="Python" /></div><div><strong>Python</strong><span>Backend + lógica de detección</span></div></div>
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/streamlit.svg" alt="Streamlit" /></div><div><strong>Streamlit</strong><span>Dashboard operativo</span></div></div>
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/sqlite.svg" alt="SQLite" /></div><div><strong>SQLite</strong><span>Persistencia local</span></div></div>
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/github.svg" alt="GitHub" /></div><div><strong>Git + GitHub</strong><span>Versionado del proyecto</span></div></div>
      </div>
      <div class="stack-section-title second-title">IA + RUNTIME</div>
      <div class="stack-grid">
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/ollama.svg" alt="Ollama" /></div><div><strong>Ollama</strong><span>Runtime LLM local</span></div></div>
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/qwen.svg" alt="Qwen" /></div><div><strong>my-qwen-3b</strong><span>Modelo local de explicación</span></div></div>
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/gnubash.svg" alt="Regex" /></div><div><strong>Regex</strong><span>Detección de patrones</span></div></div>
        <div class="tech-card"><div class="tool-logo"><img src="/assets/icons/wolfram.svg" alt="Shannon" /></div><div><strong>Shannon</strong><span>Entropía + señales estadísticas</span></div></div>
      </div>
    </div>
    <div class="quality-column">
      <div class="quality-header"><span>CALIDAD VERIFICABLE</span><div class="quality-score">37/37</div></div>
      <div class="quality-row"><div class="quality-icon green">✓</div><div><strong>Tests automatizados</strong><span>37 de 37 pruebas pasando</span></div></div>
      <div class="quality-row"><div class="quality-icon blue">✓</div><div><strong>Linting</strong><span>Código validado con herramientas de calidad</span></div></div>
      <div class="quality-row"><div class="quality-icon yellow">✓</div><div><strong>Python fijado</strong><span>Versión definida para reproducibilidad</span></div></div>
      <div class="quality-row"><div class="quality-icon purple">✓</div><div><strong>Arquitectura offline</strong><span>Sin dependencia de servicios cloud</span></div></div>
      <div class="quality-statement"><span>PRINCIPIO</span><strong>Si no puedo probarlo,<br>no debería confiar en él.</strong></div>
    </div>
  </div>
</div>

---
zoom: 0.92
---
<!-- SLIDE 10 · EVIDENCIA IA -->
<div class="slide-shell ai-evidence-slide">
  <div class="slide-heading compact-heading">
    <div class="eyebrow">10 · EVIDENCIA DE USO DE IA</div>
    <h2>La IA también fue parte del <span>equipo de desarrollo</span></h2>
  </div>
  <div class="ai-grid">
    <div v-click class="ai-card ai-green">
      <div class="ai-card-top"><span class="ai-number">01</span><span class="ai-category">ORQUESTACIÓN</span></div>
      <div class="ai-brand"><div class="brand-logo"><img src="/assets/icons/claude.svg" alt="Claude" /></div><div><strong>Claude App</strong><span>Claude Sonnet 5 / Opus</span></div></div>
      <p>Descomposición del proyecto, planificación de tareas, revisión de arquitectura y coordinación del trabajo.</p>
    </div>
    <div v-click class="ai-card ai-blue">
      <div class="ai-card-top"><span class="ai-number">02</span><span class="ai-category">EJECUCIÓN DE CÓDIGO</span></div>
      <div class="ai-brand multi-logos">
        <div class="brand-logo"><img src="/assets/icons/visual-studio-code.svg" /></div>
        <div class="brand-logo"><img src="/assets/icons/cursor.svg" alt="Cursor" /></div>
        <div class="brand-logo"><img src="/assets/icons/windsurf-black-symbol.svg" /></div>
        <div class="brand-logo"><img src="/assets/icons/opencode.svg" alt="OpenCode" /></div>
        <div class="brand-logo"><img src="/assets/icons/deepseek.svg" alt="DeepSeek Harness" style="filter:brightness(0) invert(1);" /></div>
      </div>
      <div class="ai-brand-text"><strong>VS Code · Cursor · Windsurf · OpenCode · DeepSeek Harness</strong><span>modelos free tier</span></div>
      <p>Implementación, refactorización y ejecución de tareas con múltiples IDEs y modelos vía API / OpenRouter.</p>
    </div>
    <div v-click class="ai-card ai-purple">
      <div class="ai-card-top"><span class="ai-number">03</span><span class="ai-category">VERIFICACIÓN</span></div>
      <div class="ai-brand"><div class="brand-logo"><img src="/assets/icons/deepseek-color.svg" alt="DeepSeek" /></div><div><strong>DeepSeek App</strong><span>DeepSeek-V4 Pro/Flash</span></div></div>
      <p>Contrastar afirmaciones técnicas, investigar documentación y verificar decisiones antes de incorporarlas.</p>
    </div>
    <div v-click class="ai-card ai-yellow">
      <div class="ai-card-top"><span class="ai-number">04</span><span class="ai-category">DATOS SINTÉTICOS</span></div>
      <div class="ai-brand multi-logos">
        <div class="brand-logo"><img src="/assets/icons/claude.svg" alt="Claude" /></div>
        <div class="brand-logo"><img src="/assets/icons/perplexity.svg" alt="Perplexity" /></div>
      </div>
      <div class="ai-brand-text"><strong>Claude + Perplexity</strong><span>Sonnet · Sonar free tier</span></div>
      <p>Crear escenarios de prueba, eventos sintéticos y casos diseñados para validar detección y correlación.</p>
    </div>
    <div v-click class="ai-card ai-red">
      <div class="ai-card-top"><span class="ai-number">05</span><span class="ai-category">DEBUGGING</span></div>
      <div class="ai-brand multi-logos">
        <div class="brand-logo"><img src="/assets/icons/grok.svg" alt="Grok" /></div>
        <div class="brand-logo"><img src="/assets/icons/qwen.svg" alt="Qwen" /></div>
      </div>
      <div class="ai-brand-text"><strong>Grok + Qwen</strong><span>Grok-4.6 · Qwen 3.7-Plus</span></div>
      <p>Análisis de errores, hipótesis de causa raíz y propuestas alternativas durante la depuración.</p>
    </div>
    <div v-click class="ai-card ai-multi">
      <div class="ai-card-top"><span class="ai-number">06</span><span class="ai-category">DOCUMENTACIÓN</span></div>
      <div class="ai-brand"><div class="brand-logo"><img src="/assets/icons/gemini.svg" alt="Gemini" /></div><div><strong>Gemini + NotebookLM</strong><span>Gemini 3.6 Flash free tier</span></div></div>
      <p>Síntesis de documentación, organización del conocimiento y preparación de material técnico del proyecto.</p>
    </div>
  </div>
  <div class="ai-footer">
    <span>IDEA CLAVE</span>
    <strong>La IA aceleró el desarrollo. La responsabilidad de las decisiones siguió siendo del autor.</strong>
  </div>
</div>

---

<!-- SLIDE 11 · ROADMAP -->
<div class="slide-shell roadmap-slide">
  <div class="slide-heading">
    <div class="eyebrow">11 · ROADMAP</div>
    <h2>Lo que queda fuera del MVP también es una <span>decisión</span></h2>
  </div>
  <div class="roadmap-layout">
    <div class="roadmap-now">
      <div class="roadmap-label"><span class="roadmap-dot"></span>MVP ACTUAL</div>
      <h3>Pequeño por diseño.</h3>
      <div class="now-list">
        <div>✓ Ingesta de logs pfSense</div>
        <div>✓ Persistencia SQLite</div>
        <div>✓ Heurísticas deterministas</div>
        <div>✓ Correlación de eventos</div>
        <div>✓ LLM local para explicación</div>
        <div>✓ Dashboard Streamlit</div>
      </div>
    </div>
    <div class="roadmap-line"></div>
    <div class="roadmap-future">
      <div v-click class="future-card"><div class="future-number">01</div><div><strong>Más fuentes</strong><p>Switches, IDS/IPS, servidores y endpoints.</p></div></div>
      <div v-click class="future-card"><div class="future-number">02</div><div><strong>Respuesta asistida</strong><p>Playbooks y acciones sugeridas al operador.</p></div></div>
      <div v-click class="future-card"><div class="future-number">03</div><div><strong>Modelos especializados</strong><p>LLMs y clasificadores adaptados al dominio de red.</p></div></div>
      <div v-click class="future-card"><div class="future-number">04</div><div><strong>Escalabilidad</strong><p>Procesamiento distribuido para grandes volúmenes.</p></div></div>
    </div>
  </div>
  <div class="roadmap-principle">
    <span>¿POR QUÉ NO AHORA?</span>
    <strong>Porque cada capa adicional aumenta superficie de fallo, complejidad y esfuerzo de validación.</strong>
  </div>
</div>

---

<!-- SLIDE 12 · CIERRE -->
<div class="closing-slide">
  <div class="closing-grid">
    <div class="closing-main">
      <div class="eyebrow accent-green">12 · CIERRE</div>
      <div class="closing-mark"><img class="ainoc-isotipo-sm" src="/assets/icons/diagram_animated.svg" alt="AI-NOC" /></div>
      <h1>Inteligencia artificial<br><span>donde no hay Internet.</span></h1>
      <p>AI-NOC Copilot demuestra que un entorno aislado no tiene por qué quedar fuera de la revolución de la IA.</p>
      <div class="closing-equation">
        <span>DATOS LOCALES</span> <b>+</b> <span>HEURÍSTICA</span> <b>+</b> <span>LLM LOCAL</span> <b>=</b> <strong>IA OPERATIVA</strong>
      </div>
    </div>
    <div class="closing-side">
      <div class="closing-author"><span>AUTOR</span><strong>Marcos Ruíz</strong><small>IA Estratégica: El Programador Aumentado</small></div>
      <div class="closing-repo"><span>REPOSITORIO</span><strong>github.com/0xmarcosdev/ai-noc-copilot</strong><div class="repo-bar"></div></div>
      <div class="closing-thanks"><span>Gracias</span><small>Preguntas · comentarios · demo</small></div>
    </div>
  </div>
</div>