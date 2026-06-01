"""El tutor: Claude corrige y responde, con salida estructurada + prompt caching.

Multi-idioma: el idioma objetivo (alemán/inglés) se resuelve vía `langs.py`.
Las explicaciones y traducciones son siempre en español.
"""
import anthropic
from pydantic import BaseModel

import config
import langs

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno


class VocabItem(BaseModel):
    de: str   # término en el idioma objetivo (la clave se mantiene "de" por compatibilidad)
    es: str   # glosa en español


class TutorResponse(BaseModel):
    reply: str               # tu respuesta como tutor, en el idioma objetivo
    correction: str | None   # versión corregida de lo que dijo el alumno (o null)
    explanation_es: str      # explicación en español de la corrección / gramática
    new_vocab: list[VocabItem]     # 3-6 palabras/frases nuevas útiles
    pronunciation_tip: str | None  # consejo breve de pronunciación si aplica


class WordInfo(BaseModel):
    word: str                  # palabra (forma base si aplica)
    translation_es: str        # traducción al español
    synonyms: list[str]        # 3-5 sinónimos en el idioma objetivo


def word_info(word: str, context: str = "", lang: str = "de") -> WordInfo:
    """Click en una palabra → traducción al español + sinónimos, en el idioma `lang`."""
    pack = langs.get(lang)
    msg = f"Palabra: {word}"
    if context:
        msg += f"\nContexto (frase donde aparece): {context}"
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=400,
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
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": langs.tutor_system_prompt(pack),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=history,
        output_format=TutorResponse,
    )
    return resp.parsed_output
