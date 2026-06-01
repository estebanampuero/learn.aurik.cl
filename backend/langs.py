"""Registro de idiomas (language packs) para el tutor multi-idioma.

Cada idioma define: nombre, bandera, código STT (Whisper), nivel/examen objetivo,
el contexto del alumno (para el prompt) y sus voces Piper (femenina/masculina).
Agregar un idioma = añadir una entrada aquí + descargar sus voces en el Dockerfile.

Eje fijo: la lengua de EXPLICACIÓN siempre es español (audiencia hispanohablante).
"""
from dataclasses import dataclass

VOICES_DIR = "/app/voices"


@dataclass(frozen=True)
class LangPack:
    code: str          # "de", "en"
    name_es: str       # nombre del idioma en español: "alemán"
    label: str         # etiqueta nativa para la UI: "Deutsch"
    flag: str          # emoji bandera
    stt: str           # código de idioma para Whisper
    level: str         # rango CEFR objetivo: "A1.2–A2"
    exam: str          # examen objetivo
    context: str       # quién es el alumno / su meta (va al prompt)
    vocab_focus: str   # prioridad de vocabulario
    noun_rule: str     # regla para sustantivos en el diccionario
    voices: dict       # {"f": ruta_onnx, "m": ruta_onnx}


LANGS: dict[str, LangPack] = {
    "de": LangPack(
        code="de", name_es="alemán", label="Deutsch", flag="🇩🇪", stt="de",
        level="A1.2–A2", exam="Goethe-Zertifikat A2",
        context="que se muda a Alemania a trabajar en el sector salud / MedTech",
        vocab_focus="vida diaria y contexto de salud/laboratorio",
        noun_rule="usa el artículo (der/die/das)",
        voices={
            "m": f"{VOICES_DIR}/de_DE-thorsten-medium.onnx",
            "f": f"{VOICES_DIR}/de_DE-kerstin-low.onnx",
        },
    ),
    "en": LangPack(
        code="en", name_es="inglés", label="English", flag="🇬🇧", stt="en",
        level="A2–B1", exam="Cambridge B1 Preliminary",
        context="que quiere mejorar su inglés para el trabajo, los viajes y la vida diaria",
        vocab_focus="vida diaria, trabajo y viajes",
        noun_rule="indica si es contable o incontable cuando ayude",
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


def _level_bounds(level: str) -> tuple[str, str]:
    parts = level.replace("-", "–").split("–")
    return (parts[0], parts[-1])


def tutor_system_prompt(p: LangPack) -> str:
    lo, hi = _level_bounds(p.level)
    return f"""\
Eres un profesor personal de {p.name_es} para un hispanohablante nativo (Chile) {p.context}.
Su nivel actual es {lo} y quiere llegar a {hi} y rendir el {p.exam}.

Reglas:
- Responde SIEMPRE en {p.name_es} a nivel {lo}-{hi} (frases simples, claras). Sube la
  dificultad gradualmente si el alumno responde bien.
- Si el alumno comete errores, corrígelos: da la versión corregida y explica el
  porqué en ESPAÑOL, breve.
- Mantén la conversación viva: termina tu respuesta con una pregunta sencilla.
- Introduce vocabulario útil, priorizando {p.vocab_focus}.
- Tono motivador y paciente.

Devuelve tu respuesta en el formato estructurado solicitado."""


def word_system_prompt(p: LangPack) -> str:
    return f"""\
Eres un diccionario {p.name_es}→español para un estudiante de nivel {p.level}.
Para la palabra en {p.name_es} dada, devuelve: (1) su traducción al español —breve, la acepción
más adecuada al contexto si se entrega—, y (2) 3 a 5 sinónimos en {p.name_es} de nivel similar.
Para sustantivos {p.noun_rule}; para verbos, el infinitivo."""
