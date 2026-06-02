"""Registro de tutores con especialidad. Cada idioma tiene varios profesores;
cada profesor tiene una especialidad que sesga su estilo (gramática, conversación,
negocios, viajes, entrevistas). Reutiliza voces/idiomas de langs.py.
"""
from dataclasses import dataclass

import langs


@dataclass(frozen=True)
class Tutor:
    id: str
    name: str
    lang: str           # "de" | "en"
    avatar: str         # ruta pública del frontend
    glyph: str          # iniciales para fallback
    gender: str         # "f" | "m" (voz Piper por defecto)
    specialty: str      # clave: grammar | conversation | business | travel | interviews
    specialty_es: str   # etiqueta en español
    persona: str        # cómo se comporta (va al system prompt)


TUTORS: list[Tutor] = [
    # ── Alemán ──
    Tutor("lena", "Lena", "de", "/tutors/lena.png", "LE", "f", "conversation",
          "Conversación", "cálida y conversacional; te hace hablar de tu día y mantiene el ritmo"),
    Tutor("lukas", "Lukas", "de", "/tutors/lukas.png", "LU", "m", "grammar",
          "Gramática", "metódico y claro; explica casos, declinaciones y orden de la frase con ejemplos"),
    # ── Inglés ──
    Tutor("emma", "Emma", "en", "/tutors/emma.png", "EM", "f", "conversation",
          "Conversación", "cercana y fluida; prioriza que hables con naturalidad y confianza"),
    Tutor("oliver", "Oliver", "en", "/tutors/oliver.png", "OL", "m", "business",
          "Negocios & entrevistas", "profesional; te prepara para reuniones, correos y entrevistas de trabajo"),
]

_BY_ID = {t.id: t for t in TUTORS}
DEFAULT_BY_LANG = {"de": "lena", "en": "emma"}


def get(tutor_id: str | None, lang: str = "de") -> Tutor:
    if tutor_id and tutor_id in _BY_ID:
        return _BY_ID[tutor_id]
    return _BY_ID[DEFAULT_BY_LANG.get(lang, "lena")]


def for_lang(lang: str) -> list[Tutor]:
    return [t for t in TUTORS if t.lang == lang]


def public(t: Tutor) -> dict:
    pack = langs.get(t.lang)
    return {
        "id": t.id, "name": t.name, "lang": t.lang, "avatar": t.avatar,
        "glyph": t.glyph, "gender": t.gender, "specialty": t.specialty,
        "specialty_es": t.specialty_es, "flag": pack.flag, "lang_label": pack.label,
        "greeting": pack.greeting,
    }


def persona_line(t: Tutor) -> str:
    """Frase de persona+especialidad para inyectar al system prompt del tutor."""
    return (f"Tu nombre es {t.name}. Tu especialidad es {t.specialty_es}: eres {t.persona}. "
            f"Sesga tus respuestas, correcciones y vocabulario hacia tu especialidad cuando sea natural.")
