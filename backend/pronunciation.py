"""Evaluación de pronunciación. Alcance honesto: NO es scoring acústico fonema-a-fonema
(el STT compartido solo devuelve texto). Combinamos:
  - accuracy: alineación texto objetivo vs. transcripción (qué tan bien se entendió).
  - intonation/fluency: rúbrica de Claude desde (objetivo, transcripción, duración).
"""
import re

import anthropic
from pydantic import BaseModel

import config

client = anthropic.Anthropic()


def _norm(s: str) -> list[str]:
    return re.sub(r"[^\wäöüßáéíóúñ\s]", "", s.lower(), flags=re.UNICODE).split()


def text_accuracy(target: str, transcript: str) -> int:
    """0-100 según cuántas palabras del objetivo aparecen, en orden, en la transcripción (LCS)."""
    a, b = _norm(target), _norm(transcript)
    if not a:
        return 0
    # Longest common subsequence (tolera inserciones/omisiones).
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    return round(100 * dp[m][n] / m)


class PronScore(BaseModel):
    intonation: int       # 0-100
    fluency: int          # 0-100
    tips: str             # recomendaciones específicas en español


def score(target: str, transcript: str, duration_s: float, lang: str = "de") -> dict:
    """Devuelve accuracy/intonation/fluency/overall + tips."""
    from langs import get as get_lang
    pack = get_lang(lang)
    acc = text_accuracy(target, transcript)
    words = max(1, len(_norm(target)))
    wps = words / duration_s if duration_s > 0 else 0

    try:
        resp = client.messages.parse(
            model=config.ANTHROPIC_MODEL_PRO,
            max_tokens=400,
            system=[{"type": "text", "text":
                f"Eres evaluador de pronunciación de {pack.name_es} para hispanohablantes. "
                f"Te doy la frase objetivo, lo que el STT entendió y el ritmo (palabras/segundo). "
                f"Estima entonación y fluidez (0-100) y da 1-2 recomendaciones CONCRETAS en español "
                f"(sonidos difíciles, ritmo, acento). Sé alentador pero útil."}],
            messages=[{"role": "user", "content":
                f"Objetivo: {target}\nSTT entendió: {transcript}\nRitmo: {wps:.2f} palabras/seg\n"
                f"Precisión de palabras: {acc}%"}],
            output_format=PronScore,
        )
        p = resp.parsed_output
        intonation, fluency, tips = p.intonation, p.fluency, p.tips
    except Exception:
        # Fallback sin LLM: deriva de accuracy y ritmo.
        intonation = acc
        fluency = max(0, min(100, int(100 - abs(wps - 2.0) * 25)))
        tips = "Practica leyendo en voz alta, marcando bien el final de cada frase."

    overall = round(0.5 * acc + 0.25 * intonation + 0.25 * fluency)
    return {"accuracy": acc, "intonation": intonation, "fluency": fluency,
            "overall": overall, "tips": tips, "transcript": transcript}
