# ROADMAP — AI-NOC Copilot

> Este documento responde a "¿dónde estoy y qué sigue?". Si te reincorporas
> al proyecto después de unos días y no recuerdas el estado, empieza aquí:
> mira la última casilla marcada, esa es tu punto de partida.
>
> No confundir con `DEVLOG.md` (diario de lo que ya pasó, sesión por sesión)
> ni con `SPEC.md` (arquitectura y decisiones, la fuente de verdad técnica).
> Este archivo es el checklist operativo.

## Cómo marcar el avance

Cambia `- [ ]` por `- [x]` a medida que completas cada punto. Cuando **todas**
las casillas de una fase estén marcadas, esa fase queda "cerrada": commitea,
etiqueta la versión correspondiente (ver convención abajo), y pasa a la
siguiente fase.

---

## Fase 0 — Diseño y alcance ✅ COMPLETA

- [x] Evaluar propuestas de arquitectura, descartar sobrealcance (Elastic,
      Suricata/Zeek completo, multi-sucursal real, modelos 7B+)
- [x] Definir MVP en `SPEC.md`
- [x] Esqueleto del repo (FastAPI + SQLModel + SQLite + Streamlit + Ollama nativo)

## Fase 1 — Ingesta y pipeline base ✅ COMPLETA

- [x] Listener syslog UDP (`syslog_listener.py`)
- [x] Modelo `NetworkEvent` + SQLite
- [x] Endpoints `/health`, `/events`
- [x] Tests iniciales (pytest 4/4)
- [x] Fix: SQLite no creaba la carpeta `data/`
- [x] `.env` + `python-dotenv` (sin export/set manual en Windows)
- [x] Fix: venv fijado a Python 3.11/3.12 (incompatibilidad 3.14 + SQLModel)

## Fase 2 — LLM local ✅ COMPLETA

- [x] `llm_service.py` + prompt `threat_explainer.txt`
- [x] Endpoint `POST /events/{id}/analyze`
- [x] Modelo confirmado: `my-qwen-3b:latest`
- [x] Fix: httpx keep-alive causaba "Server disconnected"
- [x] Pipeline validado end-to-end contra Ollama real

## Fase 3 — Datos sintéticos y verificación de formato ✅ COMPLETA

- [x] `scripts/generate_fake_logs.py` (escenarios: normal, bruteforce, portscan)
- [x] Formato filterlog verificado contra fuente oficial (Perplexity + BNF de
      Netgate + código fuente `pfsense/pfsense` en GitHub)
- [x] `docs/pfsense-filterlog-format.md`

## Fase 4 — Correlación de eventos 🔶 EN PROGRESO

- [x] Detectada la limitación: evento aislado de fuerza bruta = severity "low"
- [x] Regex de extracción de IP atacante desde `raw_message` (validado)
- [x] Endpoint `POST /events/correlate`
- [x] `/summary` extendido con `top_high_severity_types`
- [x] **Probar**: grupo de 10 eventos bruteforce → confirmar `severity: high`
- [x] Tests para `/events/correlate`

## Fase 5 — Dashboard visible ⬜ PENDIENTE

- [ ] Botón "Correlacionar eventos" en Streamlit
- [ ] Vista de grupos correlacionados (no solo eventos individuales)
- [ ] Mostrar `top_high_severity_types` del `/summary` en el panel derecho
- [ ] 3-4 preguntas predefinidas del chat (usar resto del Documento 31 si
      queda tiempo; si no, queda como roadmap post-curso)

## Fase 6 — Documentación y entrega ⬜ PENDIENTE

- [ ] README final revisado (instrucciones probadas de cero, sin asumir nada)
- [ ] `SPEC.md` actualizado como última pasada antes de entregar
- [ ] Evidencia de uso de IA: capturas o transcripciones de sesiones clave
      (esta conversación + DeepSeek + Perplexity ya califican, solo hay que
      exportarlas)
- [ ] `docker compose up` probado de punta a punta (Opción B del README)
- [ ] Grabación de demo: ataque simulado → detección → explicación → correlación
- [ ] Ensayo de la presentación en voz alta, cronometrado

---

## Convención de versiones

Formato: **`vMAJOR.MINOR.PATCH — "Nombre descriptivo"`**

- **MAJOR** se queda en `0` hasta que el proyecto sea un MVP demostrable
  completo. Pasa a `1.0.0` cuando termines la Fase 6.
- **MINOR** sube con cada fase cerrada (feature nueva y funcional).
- **PATCH** sube con fixes dentro de una fase ya cerrada (bugs, no features).

| Versión | Nombre | Fase | Estado |
| --- | --- | --- | --- |
| v0.1.0 | Esqueleto funcional | Fase 0-1 | ✅ hecho |
| v0.2.0 | Pipeline validado con Ollama real | Fase 2 | ✅ hecho |
| v0.3.0 | Generador de logs con formato verificado | Fase 3 | ✅ hecho |
| v0.4.0 | Correlación de eventos | Fase 4 | 🔶 en progreso |
| v0.5.0 | Dashboard completo | Fase 5 | ⬜ pendiente |
| **v1.0.0** | **MVP listo para entrega — 4 sept 2026** | Fase 6 | ⬜ pendiente |

### Cómo etiquetar en git

Cuando cierres una fase:

```cmd
git add .
git commit -m "feat: correlacion de eventos por patron de fuerza bruta"
git tag -a v0.4.0 -m "Correlacion de eventos"
git push origin main --tags
```

### Cuándo commitear (no solo cuándo etiquetar)

No esperes a cerrar una fase completa para commitear — eso es exactamente lo
que el curso pide evitar ("historial que refleje el proceso, no solo el
resultado final"). Regla simple:

- **Commitea cada vez que algo funciona y representa una sola idea completa**
  (ej. "arreglé el bug de la carpeta data", "agregué el endpoint de
  correlación") — no acumules 5 cambios distintos en un commit.
- **Prefijo del mensaje** (convención estándar, fácil de aprender):
  `feat:` (funcionalidad nueva), `fix:` (corrección de bug), `docs:`
  (documentación), `test:` (tests), `chore:` (config, dependencias).
- **Al cerrar sesión de trabajo**: commitea aunque quede algo a medias --
  mejor un commit `wip: correlacion de eventos (falta probar con Ollama)`
  que perder el punto de retomar mañana.
- **Etiqueta de versión (`git tag`)**: solo al cerrar una fase completa de
  este ROADMAP, no en cada commit.
