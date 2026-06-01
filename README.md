# Sprach-Tutor — tutor de idiomas con voz (self-hosted)

Hablas en el idioma que practicas → **faster-whisper** transcribe → **Claude** corrige y
responde → **Piper** lo dice en voz. UI web. Todo self-hosted; solo Claude usa API
(centavos/día con Haiku). Spec completa en [SPEC.md](SPEC.md).

## Idiomas y voces
- Idiomas: **alemán 🇩🇪** e **inglés 🇬🇧** (las explicaciones son siempre en español).
- Selector de **voz**: femenina ♀ / masculina ♂ por idioma (voces Piper).
- Agregar un idioma = una entrada en [`backend/langs.py`](backend/langs.py) + descargar
  sus voces en el [Dockerfile](backend/Dockerfile). Claude y Whisper ya son multilingües.

## Arquitectura
```
[Next.js UI] --audio--> [FastAPI]
                          ├─ faster-whisper (STT, local)
                          ├─ Claude (tutor + corrección, structured output + prompt caching)
                          └─ Piper (TTS multi-idioma/voz, local) --audio--> UI reproduce
```

## Correr con Docker (VPS o local)

1. `cp .env.example .env` y pon tu `ANTHROPIC_API_KEY`.
2. `docker compose up --build`
3. Abre **http://localhost:3000**

La primera build descarga el modelo Whisper (~0.5 GB) y la voz de Piper.

## ⚠️ Micrófono = requiere HTTPS (importante para el VPS)
El navegador **solo permite usar el micrófono en `localhost` o bajo HTTPS**. En el VPS:
- Pon un reverse proxy con TLS (**Caddy** o Traefik + Let's Encrypt) delante.
- Sirve el frontend en `https://tutor.tudominio.com` y el backend en `https://tutor-api.tudominio.com`.
- Ajusta `NEXT_PUBLIC_API_URL` y `CORS_ORIGINS` en `.env` a esos dominios.

Ejemplo Caddyfile:
```
tutor.tudominio.com      { reverse_proxy localhost:3000 }
tutor-api.tudominio.com  { reverse_proxy localhost:8000 }
```

## Desarrollo local (sin Docker)
- Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`
  (necesitas `ffmpeg` y los archivos de voz Piper en `voices/` — ver el Dockerfile).
- Frontend: `cd frontend && npm install && npm run dev`

## Costo
- STT (faster-whisper) + TTS (Piper): **$0** (corren local).
- Claude (Haiku 4.5): centavos/día con uso personal. Cambia el modelo con
  `DEUTSCH_TUTOR_MODEL` (ej. `claude-opus-4-8` para más calidad).

## Roadmap (ver SPEC.md)
- Fase 2: pronunciación por fonema (wav2vec2 + espeak-ng).
- Fase 3: vocabulario con repetición espaciada (Postgres) + módulo salud.
- Fase 4: simulacros Goethe A2.

## Notas de implementación (Claude API)
- `tutor.py` usa **structured outputs** (`client.messages.parse` + Pydantic) → respuesta
  siempre con `reply / correction / explanation_es / new_vocab / pronunciation_tip`.
  El idioma objetivo se resuelve en `langs.py` (prompt del tutor + del diccionario por idioma).
- El system prompt va marcado con **prompt caching** (`cache_control: ephemeral`). El caché
  rinde de verdad cuando amplías la guía del tutor (mín. ~4096 tokens en Haiku 4.5).
