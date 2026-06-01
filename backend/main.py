"""API FastAPI: orquesta STT → tutor (Claude) → TTS."""
import base64
import json
import os
import tempfile
import time

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import langs
import stt
import tts
import tutor


class WordReq(BaseModel):
    word: str
    context: str = ""
    lang: str = "de"

app = FastAPI(title="Sprach-Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/langs")
def list_langs():
    """Idiomas disponibles + voces, para poblar el selector del frontend."""
    return {
        "default": langs.DEFAULT,
        "langs": [
            {"code": p.code, "label": p.label, "flag": p.flag,
             "name_es": p.name_es, "tutor": p.tutor, "glyph": p.glyph,
             "greeting": p.greeting, "voices": sorted(p.voices.keys())}
            for p in langs.LANGS.values()
        ],
    }


@app.post("/api/word")
def word(req: WordReq):
    """Click en una palabra → traducción al español + sinónimos (idioma `lang`)."""
    info = tutor.word_info(req.word.strip(), req.context, req.lang)
    print(f"[WORD:{req.lang}] {req.word!r} -> {info.translation_es!r} syn={info.synonyms}", flush=True)
    return info.model_dump()


@app.post("/api/chat")
async def chat(
    audio: UploadFile | None = File(None),
    text: str = Form(""),
    history: str = Form("[]"),
    lang: str = Form("de"),
    voice: str = Form("f"),
):
    """Recibe audio (PTT) o texto (fallback) + historial; devuelve la respuesta del tutor."""
    hist: list[dict] = json.loads(history)
    pack = langs.get(lang)

    # 1) Obtener lo que dijo el alumno: por texto (fallback) o transcribiendo el audio (STT)
    t0 = time.monotonic()
    text = (text or "").strip()
    if text:
        user_text = text
    elif audio is not None:
        data = await audio.read()
        suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(data)
            audio_path = f.name
        try:
            user_text = stt.transcribe(audio_path, pack.stt)
        finally:
            os.remove(audio_path)
    else:
        return {"error": "Envía audio o texto."}
    t_stt = time.monotonic()

    print(f"[IN:{lang}] user_text={user_text!r} ({'text' if text else 'audio'})", flush=True)
    if not user_text:
        print("[STT] vacío → audio no entendido", flush=True)
        return {"error": "No se entendió el audio. Intenta de nuevo."}

    # 2) Tutor (Claude) responde + corrige en el idioma objetivo
    hist.append({"role": "user", "content": user_text})
    result = tutor.tutor(hist, lang)
    t_claude = time.monotonic()
    print(f"[TUTOR:{lang}] reply={result.reply!r} | corr={result.correction!r} "
          f"| vocab={[(v.de, v.es) for v in result.new_vocab]}", flush=True)

    # 3) TTS de la respuesta con la voz elegida (f/m) del idioma
    audio_bytes = tts.synthesize(result.reply, langs.voice_path(lang, voice))
    t_tts = time.monotonic()
    print(f"[TTS] {len(audio_bytes)} bytes", flush=True)
    print(f"[TIMING] stt={(t_stt-t0)*1000:.0f}ms  claude={(t_claude-t_stt)*1000:.0f}ms  "
          f"tts={(t_tts-t_claude)*1000:.0f}ms  total={(t_tts-t0)*1000:.0f}ms", flush=True)

    return {
        "user_text": user_text,
        **result.model_dump(),
        "audio_b64": base64.b64encode(audio_bytes).decode(),
    }
