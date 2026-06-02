"""Motor de exámenes CEFR: Goethe-Zertifikat (alemán) e IELTS (inglés), niveles A1–C1.

Un examen = catálogo (cert × nivel) → genera ~6-8 tareas (reading/listening/writing/speaking)
con el modelo Pro → el alumno responde tarea a tarea → corrección con rúbrica → nivel CEFR,
banda/puntos, per-skill y feedback. Listening usa TTS; speaking se responde por voz (STT).
"""
import base64

import anthropic
from pydantic import BaseModel

import config
import langs
import tts

client = anthropic.Anthropic()

CEFR = ["A1", "A2", "B1", "B2", "C1"]


def catalog(lang: str) -> list[dict]:
    """Catálogo por idioma: Goethe (de) / IELTS (en) por nivel + un test de nivel (placement)."""
    out: list[dict] = []
    if lang == "de":
        cert, cert_name = "goethe", "Goethe-Zertifikat"
    else:
        cert, cert_name = "ielts", "IELTS"
    out.append({"id": f"placement_{lang}", "cert": "placement", "level": "",
                "lang": lang, "title": "Test de nivel", "subtitle": "Descubre tu nivel CEFR",
                "emoji": "🎯", "premium": False})
    for lv in CEFR:
        out.append({"id": f"{cert}_{lv.lower()}", "cert": cert, "level": lv, "lang": lang,
                    "title": f"{cert_name} {lv}", "subtitle": f"Examen oficial nivel {lv}",
                    "emoji": "📜", "premium": True})
    return out


def _meta(exam_id: str, lang: str) -> dict | None:
    for e in catalog(lang):
        if e["id"] == exam_id:
            return e
    # tolera otro idioma
    for l in ("de", "en"):
        for e in catalog(l):
            if e["id"] == exam_id:
                return e
    return None


# ─── Generación ───────────────────────────────────────────────────────────────
class Task(BaseModel):
    type: str               # reading_mc | listening_mc | writing | speaking
    skill: str              # Lesen | Hören | Schreiben | Sprechen (o Reading/Listening/…)
    prompt: str             # consigna (español + el texto/pregunta)
    passage: str = ""       # texto a leer (reading) o frase a reproducir (listening)
    options: list[str] = [] # MC
    answer: str = ""        # correcta (MC) — privada, no se envía al cliente


class ExamTasks(BaseModel):
    tasks: list[Task]


def generate(exam_id: str, lang: str) -> tuple[dict, list[dict]]:
    """Devuelve (meta, tasks). tasks incluye 'answer' (privado) y 'audio_b64' en listening."""
    meta = _meta(exam_id, lang) or {}
    pack = langs.get(lang)
    level = meta.get("level") or "variado (A1 a C1, ascendente)"
    cert = meta.get("cert", "placement")
    framing = {
        "goethe": "estilo Goethe-Zertifikat (Lesen, Hören, Schreiben, Sprechen)",
        "ielts": "estilo IELTS (Reading, Listening, Writing, Speaking)",
        "placement": "test de nivel adaptativo (dificultad creciente de A1 a C1)",
    }.get(cert, "examen de nivel")

    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL_PRO, max_tokens=1800,
        system=[{"type": "text", "text":
            f"Eres examinador de {pack.name_es}. Crea un test {framing}, nivel {level}, con 6-8 tareas "
            f"mezclando tipos: reading_mc (con 'passage' a leer + pregunta + 4 'options' + 'answer'), "
            f"listening_mc ('passage' = frase a ESCUCHAR + pregunta en 'prompt' + 4 'options' + 'answer'), "
            f"writing (consigna corta; sin options/answer), speaking (consigna para responder hablando; "
            f"sin options/answer). Las consignas en español; los textos/opciones en {pack.name_es}. "
            f"'skill' en el idioma del examen."}],
        messages=[{"role": "user", "content": f"Genera el examen {exam_id}."}],
        output_format=ExamTasks,
    )
    voice = langs.voice_path(lang, "f")
    tasks_pub: list[dict] = []
    for i, t in enumerate(resp.parsed_output.tasks):
        d = t.model_dump()
        d["id"] = i
        if t.type == "listening_mc" and t.passage:
            audio = tts.synthesize(t.passage, voice)
            d["audio_b64"] = base64.b64encode(audio).decode()
        tasks_pub.append(d)
    return meta, tasks_pub


def public_tasks(tasks: list[dict]) -> list[dict]:
    """Quita las respuestas correctas y el passage de listening (no spoilear el audio)."""
    out = []
    for t in tasks:
        d = {k: v for k, v in t.items() if k != "answer"}
        if t.get("type") == "listening_mc":
            d.pop("passage", None)
        out.append(d)
    return out


# ─── Corrección ───────────────────────────────────────────────────────────────
class SkillScore(BaseModel):
    skill: str
    score: int


class Grade(BaseModel):
    cefr_level: str           # A1..C1 alcanzado
    score: int                # 0-100
    band: str                 # IELTS band (ej. "5.5") o Goethe ("72/100 Punkte")
    passed: bool
    per_skill: list[SkillScore]
    feedback: str
    recommendations: list[str]


def grade(meta: dict, tasks: list[dict], answers: list[str], lang: str) -> dict:
    pack = langs.get(lang)
    cert = meta.get("cert", "placement")
    target = meta.get("level", "")
    band_kind = "banda IELTS (1-9, ej. 6.0)" if cert == "ielts" else \
                ("Goethe Punkte (ej. 78/100)" if cert == "goethe" else "puntaje (0-100)")

    lines = []
    for i, t in enumerate(tasks):
        ans = answers[i] if i < len(answers) else ""
        corr = f" | correcta: {t.get('answer')}" if t.get("answer") else ""
        lines.append(f"[{t.get('skill')}] {t.get('prompt')} {t.get('passage','')}\n  respuesta: {ans}{corr}")
    body = "\n".join(lines)

    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL_PRO, max_tokens=1100,
        system=[{"type": "text", "text":
            f"Eres examinador oficial de {pack.name_es} ({cert}). Evalúa las respuestas con rigor y "
            f"devuelve: cefr_level (A1..C1 realmente alcanzado), score 0-100, band como {band_kind}, "
            f"passed (¿alcanza el nivel objetivo {target or 'estimado'}?), per_skill (lista skill/score 0-100), "
            f"feedback (español, claro y motivador), recommendations (lista en español)."}],
        messages=[{"role": "user", "content": f"Nivel objetivo: {target or '(placement)'}\n\n{body}"}],
        output_format=Grade,
    )
    return resp.parsed_output.model_dump()
