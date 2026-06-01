"""API FastAPI: orquesta STT → tutor (Claude) → TTS."""
import base64
import json
import os
import tempfile
import time

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import stt
import tts
import tutor


class WordReq(BaseModel):
    word: str
    context: str = ""

app = FastAPI(title="Deutsch-Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/word")
def word(req: WordReq):
    """Click en una palabra alemana → traducción al español + sinónimos."""
    info = tutor.word_info(req.word.strip(), req.context)
    print(f"[WORD] {req.word!r} -> {info.translation_es!r} syn={info.synonyms_de}", flush=True)
    return info.model_dump()


@app.post("/api/chat")
async def chat(audio: UploadFile = File(...), history: str = Form("[]")):
    """Recibe audio (lo que dijo el alumno) + historial; devuelve la respuesta del tutor."""
    hist: list[dict] = json.loads(history)

    # 1) Guardar audio y transcribir (STT)
    data = await audio.read()
    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        audio_path = f.name
    t0 = time.monotonic()
    try:
        user_text = stt.transcribe(audio_path)
    finally:
        os.remove(audio_path)
    t_stt = time.monotonic()

    print(f"[STT] user_text={user_text!r}", flush=True)
    if not user_text:
        print("[STT] vacío → audio no entendido", flush=True)
        return {"error": "No se entendió el audio. Intenta de nuevo."}

    # 2) Tutor (Claude) responde + corrige
    hist.append({"role": "user", "content": user_text})
    result = tutor.tutor(hist)
    t_claude = time.monotonic()
    print(f"[TUTOR] reply={result.reply_de!r} | corr={result.correction!r} "
          f"| vocab={[(v.de, v.es) for v in result.new_vocab]}", flush=True)

    # 3) TTS de la respuesta en alemán
    audio_bytes = tts.synthesize(result.reply_de)
    t_tts = time.monotonic()
    print(f"[TTS] {len(audio_bytes)} bytes", flush=True)
    print(f"[TIMING] stt={(t_stt-t0)*1000:.0f}ms  claude={(t_claude-t_stt)*1000:.0f}ms  "
          f"tts={(t_tts-t_claude)*1000:.0f}ms  total={(t_tts-t0)*1000:.0f}ms", flush=True)

    return {
        "user_text": user_text,
        **result.model_dump(),
        "audio_b64": base64.b64encode(audio_bytes).decode(),
    }
