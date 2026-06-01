# Deutsch-Tutor — plataforma self-hosted de alemán con voz + pronunciación

> Tutor de alemán personalizado (A1.2 → A2 → B1, contexto salud/MedTech) con **conversación
> por voz** y **evaluación de pronunciación real** (lo que el modo voz de un LLM no hace).
> Self-hosted, casi gratis, y doble como **proyecto de portafolio** para roles MedTech/AI.
> Proyecto separado (puedes moverlo a su propio repo cuando quieras).

## Objetivo
1. Hablar con un tutor en alemán a mi nivel, que **corrige gramática y vocabulario**.
2. **Drills de pronunciación** con scoring **por fonema** (feedback fonético de verdad).
3. Vocabulario con **repetición espaciada (SRS)**, enfocado en mis errores + vocab de salud.
4. Preparación **Goethe-Zertifikat A2**.

## Stack (tu stack, todo self-hostable)
| Capa | Tecnología | Costo |
|---|---|---|
| Frontend | **Next.js** (React) | $0 |
| Backend | **FastAPI** (Python) | $0 |
| STT (voz→texto) | **faster-whisper** (self-hosted; ya lo usas) | $0 |
| TTS (texto→voz) | **Piper** (open-source, voces alemanas locales) | $0 |
| LLM (cerebro tutor) | **Claude API** (Haiku=barato / Sonnet=mejor) · o local con Ollama | centavos/día |
| **Pronunciación** | **wav2vec2 phoneme** + **espeak-ng** (alineación GOP) | $0 |
| DB | **PostgreSQL + pgvector** (SRS, vocab, progreso) | $0 |
| Deploy | **Docker Compose** en tu VPS / local | $0 |

## Arquitectura (flujo)

```
[Next.js UI] ──mic audio──> [FastAPI]
                               ├─ faster-whisper  → texto de lo que dijiste
                               ├─ Claude (tutor)  → respuesta A2 + corrección (JSON)
                               ├─ Piper TTS       → audio de la respuesta ──> UI reproduce
                               └─ Pronunciation:
                                     wav2vec2 (fonemas dichos)
                                     vs espeak-ng (fonemas esperados del target)
                                     → score por fonema ──> UI resalta errores
        [Postgres+pgvector] ← vocab, SRS, errores frecuentes, progreso
```

## Alcance por fases (MVP primero)

### Fase 1 — MVP "conversación con corrección" (1-2 días)
- Botón de micrófono → faster-whisper transcribe.
- Claude responde como tutor (alemán A2 + explicación en español + corrección de errores),
  devolviendo JSON: `{respuesta_de, correccion, explicacion_es, vocab_nuevo[]}`.
- Piper reproduce la respuesta en alemán.
- UI muestra: lo que dijiste, la corrección, el vocab nuevo.

### Fase 2 — Pronunciación por fonema (2-3 días)
- La app muestra una frase alemana + reproduce el audio nativo (Piper).
- Grabas → wav2vec2 (modelo de fonemas) saca tu secuencia fonética.
- espeak-ng genera la secuencia fonética esperada del target.
- Alineas (GOP / edit-distance) → **score por fonema** → UI resalta los que fallaste.

### Fase 3 — SRS + módulos
- Vocabulario con repetición espaciada (algoritmo SM-2) en Postgres.
- Módulo de vocab de **salud/laboratorio** (tu diferenciador).
- Tracking de progreso + errores frecuentes (Claude los usa para insistir).

### Fase 4 — Examen Goethe A2
- Simulacros (Hören/Lesen/Schreiben/Sprechen) generados por Claude + corregidos.

## Estructura de carpetas (propuesta)
```
deutsch-tutor/
├── docker-compose.yml
├── backend/            (FastAPI)
│   ├── main.py
│   ├── stt.py          (faster-whisper)
│   ├── tts.py          (Piper)
│   ├── tutor.py        (Claude: persona + corrección, prompt cacheado)
│   ├── pronunciation.py(wav2vec2 + espeak-ng)
│   └── db.py           (Postgres/pgvector, SRS)
├── frontend/           (Next.js)
│   └── app/            (UI: grabar, conversar, drills)
└── README.md
```

## Decisiones a confirmar
1. **LLM:** ¿Claude API (recomendado: mejor calidad de tutor, centavos/día con Haiku) o
   100% local con Ollama (offline, $0, pero peor calidad pedagógica)?
2. **Dónde correr:** ¿tu Mac (dev) primero, luego VPS? ¿Tienes GPU o solo CPU? (faster-whisper
   y wav2vec2 corren en CPU, solo más lento.)
3. **¿Arrancamos por el MVP de la Fase 1** (conversación con corrección) y luego sumamos pronunciación?
