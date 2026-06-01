"""El tutor: Claude corrige y responde, con salida estructurada + prompt caching.

Multi-idioma: el idioma objetivo (alemán/inglés) se resuelve vía `langs.py`.
Las explicaciones y traducciones son siempre en español. Los tutores son generales
(se adaptan al nivel del alumno).
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
    grammar: Grammar | None         # mini-ficha de gramática (o null)
    new_vocab: list[VocabItem]      # 2-4 palabras/frases útiles
    pronunciation_tip: str | None   # consejo de pronunciación (o null)


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


def tutor(history: list[dict], lang: str = "de") -> TutorResponse:
    """history: lista de {"role": "user"|"assistant", "content": str}. `lang` = idioma objetivo."""
    pack = langs.get(lang)
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1200,
        system=[{
            "type": "text",
            "text": langs.tutor_system_prompt(pack),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=history,
        output_format=TutorResponse,
    )
    return resp.parsed_output
