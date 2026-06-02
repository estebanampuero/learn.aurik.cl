"""El tutor: Claude corrige y responde, con salida estructurada + prompt caching.

Multi-idioma: el idioma objetivo (alemán/inglés) se resuelve vía `langs.py`.
Las explicaciones y traducciones son siempre en español. Los tutores son generales
(se adaptan al nivel del alumno) y tienen especialidad (vía tutors.py).
"""
import anthropic
from pydantic import BaseModel

import config
import langs

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno


class VocabItem(BaseModel):
    de: str   # término en el idioma objetivo (la clave se mantiene "de" por compatibilidad)
    es: str   # glosa en español


class CorrectionItem(BaseModel):
    wrong: str
    right: str
    category: str = "general"   # grammar | vocabulary | spelling | word_order | …


class Grammar(BaseModel):
    tag: str       # categoría corta, ej. "Verbos impersonales"
    title: str     # nombre de la regla, ej. "es geht + Dativ"
    rule: str      # explicación en español
    example: str   # 1-2 ejemplos en el idioma objetivo


class TutorResponse(BaseModel):
    reply: str                      # respuesta del tutor, en el idioma objetivo
    reply_translation_es: str       # traducción al español de la respuesta
    correction: str | None          # frase corregida completa (o null)
    correction_items: list[CorrectionItem]  # pares wrong→right (vacío si no hubo)
    explanation_es: str             # explicación breve en español
    similar_examples: list[str]     # 1-3 ejemplos parecidos a la corrección (refuerzo)
    grammar: Grammar | None         # mini-ficha de gramática (o null)
    new_vocab: list[VocabItem]      # 2-4 palabras/frases útiles
    pronunciation_tip: str | None   # consejo de pronunciación (o null)
    level_estimate: str | None      # nivel CEFR estimado del alumno: A1..C2 (o null)
    objectives_done: list[str]      # objetivos del escenario YA cumplidos (cumulativo; [] si no hay)


class WordInfo(BaseModel):
    word: str                  # palabra (forma base si aplica)
    pos: str                   # categoría gramatical (ej. "sustantivo · der")
    ipa: str                   # transcripción IPA aproximada (o "")
    translation_es: str        # traducción al español
    synonyms: list[str]        # 2-5 sinónimos en el idioma objetivo
    example_de: str            # frase de ejemplo en el idioma objetivo
    example_es: str            # traducción al español del ejemplo


def word_info(word: str, context: str = "", lang: str = "de") -> WordInfo:
    """Click en una palabra → ficha de diccionario (idioma `lang` → español)."""
    pack = langs.get(lang)
    msg = f"Palabra: {word}"
    if context:
        msg += f"\nContexto (frase donde aparece): {context}"
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=500,
        system=[{
            "type": "text",
            "text": langs.word_system_prompt(pack),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": msg}],
        output_format=WordInfo,
    )
    return resp.parsed_output


def tutor(history: list[dict], lang: str = "de", extra_system: str = "") -> TutorResponse:
    """history: lista de {"role": "user"|"assistant", "content": str}. `lang` = idioma objetivo.

    `extra_system` agrega persona/especialidad del tutor, escenario y memoria del alumno.
    """
    pack = langs.get(lang)
    system_text = langs.tutor_system_prompt(pack)
    if extra_system:
        system_text += "\n\n" + extra_system
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1300,
        system=[{
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=history,
        output_format=TutorResponse,
    )
    return resp.parsed_output


# ─── Traducción instantánea (palabra / frase / mensaje) ───────────────────────
class Translation(BaseModel):
    translation_es: str
    note: str = ""   # matiz útil (registro, falso amigo…) o vacío


def translate(text: str, mode: str = "message", lang: str = "de") -> Translation:
    pack = langs.get(lang)
    kind = {"word": "una palabra", "phrase": "una frase", "message": "un mensaje"}.get(mode, "un texto")
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=400,
        system=[{"type": "text", "text":
            f"Eres traductor de {pack.name_es} a español. Traduce {kind} con naturalidad. "
            f"Si hay un matiz útil (registro formal/informal, falso amigo, modismo), ponlo en 'note'; "
            f"si no, deja 'note' vacío."}],
        messages=[{"role": "user", "content": text}],
        output_format=Translation,
    )
    return resp.parsed_output


# ─── Generación de flashcards desde vocabulario + errores ─────────────────────
class FlashcardOut(BaseModel):
    mode: str           # multiple_choice | fill_blank | reverse
    front: str          # pregunta / prompt
    back: str           # respuesta correcta
    options: list[str]  # opciones (multiple_choice) o vacío
    hint: str = ""


class FlashcardBatch(BaseModel):
    cards: list[FlashcardOut]


def generate_flashcards(words: list[dict], errors: list[dict], lang: str = "de") -> list[FlashcardOut]:
    """Crea tarjetas variadas (3 modos) desde palabras guardadas y errores frecuentes."""
    pack = langs.get(lang)
    vocab_txt = "\n".join(f"- {w.get('word')} = {w.get('translation_es')}" for w in words[:20]) or "(sin palabras)"
    err_txt = "\n".join(f"- '{e.get('wrong')}' → '{e.get('right')}'" for e in errors[:12] if e.get("wrong")) or "(sin errores)"
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL_PRO,
        max_tokens=1500,
        system=[{"type": "text", "text":
            f"Eres generador de flashcards de {pack.name_es} para un hispanohablante. Crea tarjetas "
            f"variando los 3 modos: 'multiple_choice' (front = pregunta, options = 4 alternativas, "
            f"back = la correcta), 'fill_blank' (front = frase con un hueco '___', back = la palabra), "
            f"'reverse' (front = palabra/frase en español, back = en {pack.name_es}). "
            f"Usa el vocabulario y refuerza los errores. front/back claros y breves."}],
        messages=[{"role": "user", "content":
            f"VOCABULARIO:\n{vocab_txt}\n\nERRORES A REFORZAR:\n{err_txt}\n\n"
            f"Genera entre 6 y 12 tarjetas, mezclando los 3 modos."}],
        output_format=FlashcardBatch,
    )
    return resp.parsed_output.cards
