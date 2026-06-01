"""El tutor: Claude corrige y responde, con salida estructurada + prompt caching."""
import anthropic
from pydantic import BaseModel

import config

client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno

# System prompt estable → marcado para prompt caching. (Nota: el caché solo se
# activa si el prefijo alcanza el mínimo del modelo —4096 tokens en Haiku 4.5—;
# si amplías esta guía con más reglas/ejemplos, el caché empieza a ahorrar.)
SYSTEM_PROMPT = """\
Eres un profesor personal de alemán para un hispanohablante nativo (Chile) que se
muda a Alemania a trabajar en el sector salud / MedTech. Su nivel actual es A1.2 y
quiere llegar a A2 y rendir el Goethe-Zertifikat A2.

Reglas:
- Responde SIEMPRE en alemán a nivel A1.2-A2 (frases simples, claras). Sube la
  dificultad gradualmente si el alumno responde bien.
- Si el alumno comete errores, corrígelos: da la versión corregida y explica el
  porqué en ESPAÑOL, breve.
- Mantén la conversación viva: termina tu respuesta con una pregunta sencilla.
- Introduce vocabulario útil, priorizando vida diaria y contexto de salud/laboratorio.
- Tono motivador y paciente.

Devuelve tu respuesta en el formato estructurado solicitado."""


class VocabItem(BaseModel):
    de: str
    es: str


class TutorResponse(BaseModel):
    reply_de: str            # tu respuesta como tutor, en alemán (A2)
    correction: str | None   # versión corregida de lo que dijo el alumno (o null)
    explanation_es: str      # explicación en español de la corrección / gramática
    new_vocab: list[VocabItem]   # 3-6 palabras/frases nuevas útiles
    pronunciation_tip: str | None  # consejo breve de pronunciación si aplica


class WordInfo(BaseModel):
    word: str                  # palabra (forma base si aplica)
    translation_es: str        # traducción al español
    synonyms_de: list[str]     # 3-5 sinónimos en alemán


_WORD_SYS = """Eres un diccionario alemán→español para un estudiante de nivel A2.
Para la palabra alemana dada, devuelve: (1) su traducción al español —breve, la acepción
más adecuada al contexto si se entrega—, y (2) 3 a 5 sinónimos en alemán de nivel similar.
Para sustantivos usa el artículo (der/die/das); para verbos, el infinitivo."""


def word_info(word: str, context: str = "") -> WordInfo:
    msg = f"Palabra: {word}"
    if context:
        msg += f"\nContexto (frase donde aparece): {context}"
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=400,
        system=[{"type": "text", "text": _WORD_SYS, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": msg}],
        output_format=WordInfo,
    )
    return resp.parsed_output


def tutor(history: list[dict]) -> TutorResponse:
    """history: lista de {"role": "user"|"assistant", "content": str}."""
    resp = client.messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=history,
        output_format=TutorResponse,
    )
    return resp.parsed_output
