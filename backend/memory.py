"""Memoria permanente del alumno: errores recurrentes, temas, nivel y objetivos.

Se inyecta como bloque de texto al system prompt del tutor para que "recuerde" entre
sesiones. Se nutre del ErrorLog y de las conversaciones guardadas.
"""
from collections import Counter

from sqlmodel import Session, select

from models import ErrorLog, Conversation, User, SavedWord


def record_errors(session: Session, user_id: int, lang: str, items: list[dict], explanation: str = "") -> None:
    """Guarda cada corrección (wrong→right) como ErrorLog para nutrir la memoria/estadísticas."""
    for it in items or []:
        wrong = (it.get("wrong") or "").strip()
        right = (it.get("right") or "").strip()
        if not wrong and not right:
            continue
        session.add(ErrorLog(
            user_id=user_id, lang=lang,
            category=(it.get("category") or "general"),
            wrong=wrong, right=right, explanation=explanation[:400],
        ))


def build_block(session: Session, user: User, lang: str) -> str:
    """Compone el bloque de memoria para el prompt del tutor (o cadena vacía si no hay nada)."""
    parts: list[str] = []

    level = user.level_de if lang == "de" else user.level_en
    parts.append(f"Nivel estimado del alumno: {level}.")

    if user.goals:
        parts.append(f"Objetivos del alumno: {user.goals}.")

    # Errores recurrentes: top categorías + ejemplos recientes.
    errs = session.exec(
        select(ErrorLog).where(ErrorLog.user_id == user.id, ErrorLog.lang == lang)
        .order_by(ErrorLog.created_at.desc()).limit(40)
    ).all()
    if errs:
        cats = Counter(e.category for e in errs)
        top = ", ".join(f"{c} ({n})" for c, n in cats.most_common(3))
        samples = "; ".join(f"'{e.wrong}'→'{e.right}'" for e in errs[:4] if e.wrong)
        parts.append(f"Errores frecuentes: {top}. Ejemplos: {samples}.")

    # Temas ya trabajados (escenarios recientes).
    convs = session.exec(
        select(Conversation).where(Conversation.user_id == user.id, Conversation.lang == lang)
        .order_by(Conversation.updated_at.desc()).limit(8)
    ).all()
    topics = [c.scenario_id for c in convs if c.scenario_id]
    if topics:
        parts.append("Temas recientes: " + ", ".join(dict.fromkeys(topics)) + ".")

    words = session.exec(
        select(SavedWord).where(SavedWord.user_id == user.id, SavedWord.lang == lang)
        .order_by(SavedWord.learned_at.desc()).limit(8)
    ).all()
    if words:
        parts.append("Vocabulario que está aprendiendo: " + ", ".join(w.word for w in words) + ".")

    if not parts:
        return ""
    return ("MEMORIA DEL ALUMNO (úsala para personalizar y para reforzar lo que le cuesta, "
            "sin mencionarla explícitamente):\n- " + "\n- ".join(parts))
