"""Registro de idiomas (language packs) para el tutor multi-idioma "Sona".

Cada idioma define: tutor (nombre + iniciales), código STT (Whisper), contexto del
alumno, voces Piper (♀/♂) y los prompts (tutor + diccionario) por idioma.
Agregar un idioma = añadir una entrada aquí + descargar sus voces en el Dockerfile.

Eje fijo: la lengua de EXPLICACIÓN siempre es español (audiencia hispanohablante).
Los tutores son GENERALES: detectan y se adaptan al nivel del alumno (no fijos a un nivel).
"""
from dataclasses import dataclass

VOICES_DIR = "/app/voices"


@dataclass(frozen=True)
class LangPack:
    code: str          # "de", "en"
    name_es: str       # nombre del idioma en español: "alemán"
    label: str         # etiqueta nativa para la UI: "Deutsch"
    flag: str          # emoji bandera
    tutor: str         # nombre del tutor (persona): "Lena"
    glyph: str         # iniciales para el avatar fallback: "DE"
    stt: str           # código de idioma para Whisper
    context: str       # quién es el alumno / su meta (va al prompt)
    vocab_focus: str   # prioridad de vocabulario
    noun_rule: str     # regla para sustantivos en el diccionario
    greeting: str      # saludo inicial del tutor (en el idioma objetivo)
    voices: dict       # {"f": ruta_onnx, "m": ruta_onnx}


LANGS: dict[str, LangPack] = {
    "de": LangPack(
        code="de", name_es="alemán", label="Deutsch", flag="🇩🇪",
        tutor="Lena", glyph="DE", stt="de",
        context="que se muda a Alemania a trabajar en el sector salud / MedTech",
        vocab_focus="vida diaria y contexto de salud/laboratorio",
        noun_rule="usa el artículo (der/die/das)",
        greeting="Hallo! Schön, dich zu sehen. Wie geht es dir heute?",
        voices={
            "m": f"{VOICES_DIR}/de_DE-thorsten-medium.onnx",
            "f": f"{VOICES_DIR}/de_DE-kerstin-low.onnx",
        },
    ),
    "en": LangPack(
        code="en", name_es="inglés", label="English", flag="🇬🇧",
        tutor="Emma", glyph="EN", stt="en",
        context="que quiere mejorar su inglés para el trabajo, los viajes y la vida diaria",
        vocab_focus="vida diaria, trabajo y viajes",
        noun_rule="indica si es contable o incontable cuando ayude",
        greeting="Hi! Great to see you. How are you doing today?",
        voices={
            "m": f"{VOICES_DIR}/en_US-ryan-medium.onnx",
            "f": f"{VOICES_DIR}/en_US-amy-medium.onnx",
        },
    ),
}

DEFAULT = "de"


def get(code: str | None) -> LangPack:
    return LANGS.get(code or "", LANGS[DEFAULT])


def voice_path(code: str | None, gender: str | None) -> str:
    pack = get(code)
    g = gender if gender in ("f", "m") else "f"
    return pack.voices[g]


def tutor_system_prompt(p: LangPack) -> str:
    return f"""\
Eres {p.tutor}, tutor/a personal de {p.name_es} para un hispanohablante nativo (Chile) {p.context}.

Eres un tutor GENERAL, no atado a un nivel fijo: **detecta el nivel del alumno por cómo
escribe/habla y adáptate** — usa frases más simples si recién empieza y más complejas si
avanza. Nunca lo abrumes ni lo subestimes.

Reglas:
- Responde SIEMPRE en {p.name_es}, en el nivel que calce con el alumno. Sube la dificultad
  de a poco si responde bien.
- Mantén la conversación viva: termina con una pregunta sencilla.
- Introduce vocabulario útil, priorizando {p.vocab_focus}.
- Tono cálido, motivador y paciente.

Campos de la respuesta estructurada:
- reply: tu respuesta como tutor, en {p.name_es}.
- reply_translation_es: la traducción al español de tu propia respuesta.
- correction: si el alumno cometió errores, la frase corregida completa (o null si no hubo).
- correction_items: lista de pares {{wrong, right}} con cada trozo corregido (vacía si no hubo).
- explanation_es: explicación BREVE en español de la corrección.
- grammar: si aplica, una mini-ficha {{tag, title, rule, example}} de la regla gramatical
  (tag = categoría corta; title = nombre de la regla; rule = explicación en español;
  example = 1-2 ejemplos en {p.name_es}). null si no hay regla relevante.
- new_vocab: 2-4 palabras/frases útiles, cada una {{de, es}} (de = término en {p.name_es}, es = glosa en español).
- pronunciation_tip: consejo breve de pronunciación, o null."""


def word_system_prompt(p: LangPack) -> str:
    return f"""\
Eres un diccionario {p.name_es}→español. Para la palabra en {p.name_es} dada, devuelve:
- word: la palabra (forma base si aplica; para sustantivos {p.noun_rule}; verbos en infinitivo).
- pos: categoría gramatical breve en español (ej. "sustantivo · der", "verbo", "adjetivo").
- ipa: transcripción IPA aproximada (ej. "/ˈmyːdə/"). Si no aplica, cadena vacía.
- translation_es: traducción al español, breve, la acepción más adecuada al contexto si se da.
- synonyms: 2-5 sinónimos en {p.name_es} de nivel similar.
- example_de: una frase de ejemplo corta en {p.name_es} usando la palabra.
- example_es: la traducción al español de esa frase."""
