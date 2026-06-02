"""Juegos: generan contenido con el modelo Pro y reutilizan TTS / pronunciación.

- voice: frases para leer en voz alta (scoring vía /api/pronunciation existente).
- listening: frase con audio TTS + opciones de traducción (1 correcta + distractores).
- sentence: frase desordenada en fichas para reordenar (orden + gramática).
- match: pares palabra↔traducción (memoria); usa el vocabulario guardado o genera.
"""
import base64
import random

import anthropic
from pydantic import BaseModel

import config
import langs
import tts

client = anthropic.Anthropic()


def _level_of(user_level: str) -> str:
    return user_level if user_level in {"A1", "A2", "B1", "B2", "C1", "C2"} else "A2"


# ─── Reto de voz ──────────────────────────────────────────────────────────────
class VoiceBatch(BaseModel):
    phrases: list[str]


def voice_rounds(lang: str, level: str, n: int = 6) -> list[str]:
    pack = langs.get(lang)
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL_PRO, max_tokens=600,
        system=[{"type": "text", "text":
            f"Genera {n} frases CORTAS y útiles en {pack.name_es}, nivel {level}, para practicar "
            f"pronunciación en voz alta. Cotidianas, naturales, de 4-9 palabras. Solo las frases."}],
        messages=[{"role": "user", "content": "Genera las frases."}],
        output_format=VoiceBatch,
    )
    return resp.parsed_output.phrases[:n]


# ─── ¿Qué escuchaste? (listening) ─────────────────────────────────────────────
class ListeningItem(BaseModel):
    sentence: str          # en el idioma objetivo (se reproduce)
    translation_es: str    # opción correcta
    distractors: list[str] # 3 traducciones incorrectas pero plausibles


class ListeningBatch(BaseModel):
    items: list[ListeningItem]


def listening_rounds(lang: str, level: str, gender: str = "f", n: int = 5) -> list[dict]:
    pack = langs.get(lang)
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL_PRO, max_tokens=900,
        system=[{"type": "text", "text":
            f"Genera {n} frases en {pack.name_es}, nivel {level}, cada una con su traducción al español "
            f"(correcta) y 3 traducciones INCORRECTAS pero plausibles (distractores). Para un juego de "
            f"comprensión auditiva."}],
        messages=[{"role": "user", "content": "Genera los ítems."}],
        output_format=ListeningBatch,
    )
    out = []
    voice = langs.voice_path(lang, gender)
    for it in resp.parsed_output.items[:n]:
        options = [it.translation_es] + it.distractors[:3]
        random.shuffle(options)
        audio = tts.synthesize(it.sentence, voice)
        out.append({
            "sentence": it.sentence,
            "audio_b64": base64.b64encode(audio).decode(),
            "options": options,
            "correct": it.translation_es,
        })
    return out


# ─── Arma la frase (sentence builder) ─────────────────────────────────────────
class SentenceItem(BaseModel):
    sentence: str          # frase correcta en el idioma objetivo
    translation_es: str


class SentenceBatch(BaseModel):
    items: list[SentenceItem]


def sentence_rounds(lang: str, level: str, n: int = 6) -> list[dict]:
    pack = langs.get(lang)
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL_PRO, max_tokens=700,
        system=[{"type": "text", "text":
            f"Genera {n} frases en {pack.name_es}, nivel {level}, de 4-8 palabras, naturales, con su "
            f"traducción al español. Para un juego de ordenar palabras."}],
        messages=[{"role": "user", "content": "Genera las frases."}],
        output_format=SentenceBatch,
    )
    out = []
    for it in resp.parsed_output.items[:n]:
        tokens = it.sentence.rstrip(".!?").split()
        shuffled = tokens[:]
        if len(shuffled) > 1:
            while shuffled == tokens:
                random.shuffle(shuffled)
        out.append({"answer": it.sentence.rstrip(".!?"), "tokens": shuffled,
                    "translation_es": it.translation_es})
    return out


# ─── Memoria / Match ──────────────────────────────────────────────────────────
class MatchPair(BaseModel):
    word: str
    es: str


class MatchBatch(BaseModel):
    pairs: list[MatchPair]


def match_pairs(lang: str, level: str, saved: list[dict], n: int = 6) -> list[dict]:
    """Usa el vocabulario guardado; si no alcanza, completa con palabras generadas."""
    pairs = [{"word": w["word"], "es": w["translation_es"]} for w in saved if w.get("translation_es")][:n]
    if len(pairs) < n:
        pack = langs.get(lang)
        resp = client.messages.parse(
            model=config.ANTHROPIC_MODEL_PRO, max_tokens=500,
            system=[{"type": "text", "text":
                f"Genera {n - len(pairs)} palabras útiles en {pack.name_es}, nivel {level}, con su "
                f"traducción al español. Para un juego de emparejar."}],
            messages=[{"role": "user", "content": "Genera los pares."}],
            output_format=MatchBatch,
        )
        have = {p["word"].lower() for p in pairs}
        for p in resp.parsed_output.pairs:
            if p.word.lower() not in have:
                pairs.append({"word": p.word, "es": p.es})
            if len(pairs) >= n:
                break
    return pairs[:n]
