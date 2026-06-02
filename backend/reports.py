"""Informe semanal y plan de estudio personalizado (modelo Pro de Claude)."""
from collections import Counter
from datetime import datetime, timedelta

import anthropic
from pydantic import BaseModel
from sqlmodel import Session, select, func

import config
import langs
from models import (User, ErrorLog, SavedWord, Conversation, Message,
                    PronunciationAttempt, ProgressEvent)

client = anthropic.Anthropic()


# ─── Informe semanal ──────────────────────────────────────────────────────────
class WeeklyContent(BaseModel):
    summary: str            # resumen de avances (español)
    frequent_errors: list[str]
    new_words: list[str]
    recommendations: list[str]


def weekly_report(session: Session, user: User, lang: str) -> dict:
    since = datetime.utcnow() - timedelta(days=7)

    errs = session.exec(select(ErrorLog).where(
        ErrorLog.user_id == user.id, ErrorLog.lang == lang, ErrorLog.created_at >= since)).all()
    words = session.exec(select(SavedWord).where(
        SavedWord.user_id == user.id, SavedWord.lang == lang, SavedWord.learned_at >= since)).all()
    convs = session.exec(select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user.id, Conversation.lang == lang,
        Conversation.created_at >= since)).one()
    msgs = session.exec(select(func.count()).select_from(Message).join(Conversation).where(
        Conversation.user_id == user.id, Message.role == "user",
        Message.created_at >= since)).one()
    xp = session.exec(select(func.coalesce(func.sum(ProgressEvent.xp), 0)).where(
        ProgressEvent.user_id == user.id, ProgressEvent.created_at >= since)).one()

    err_samples = "; ".join(f"'{e.wrong}'→'{e.right}'" for e in errs[:12] if e.wrong) or "ninguno"
    word_list = ", ".join(w.word for w in words[:20]) or "ninguna"
    pack = langs.get(lang)
    level = user.level_de if lang == "de" else user.level_en

    try:
        resp = client.messages.parse(
            model=config.ANTHROPIC_MODEL_PRO,
            max_tokens=900,
            system=[{"type": "text", "text":
                f"Eres tutor de {pack.name_es}. Redacta el informe SEMANAL del alumno en español, "
                f"motivador y concreto. Nivel actual: {level}."}],
            messages=[{"role": "user", "content":
                f"Datos de la semana:\n- Conversaciones: {convs}\n- Mensajes: {msgs}\n- XP: {xp}\n"
                f"- Palabras nuevas: {word_list}\n- Errores: {err_samples}\n"
                f"Genera: summary, frequent_errors (lista), new_words (lista), recommendations (lista)."}],
            output_format=WeeklyContent,
        )
        c = resp.parsed_output.model_dump()
    except Exception:
        cats = Counter(e.category for e in errs)
        c = {
            "summary": f"Esta semana tuviste {convs} conversaciones y {msgs} mensajes ({xp} XP).",
            "frequent_errors": [f"{k} ({v})" for k, v in cats.most_common(5)],
            "new_words": [w.word for w in words[:20]],
            "recommendations": ["Repasa tus flashcards a diario.", "Practica una conversación nueva."],
        }
    c["stats"] = {"conversations": int(convs), "messages": int(msgs), "xp": int(xp),
                  "new_words": len(words), "level": level}
    return c


# ─── Plan de estudio ──────────────────────────────────────────────────────────
class PlanItem(BaseModel):
    day: str
    focus: str
    activity: str


class StudyContent(BaseModel):
    objectives: list[str]
    weekly_schedule: list[PlanItem]
    topics: list[str]


def study_plan(session: Session, user: User, lang: str) -> dict:
    errs = session.exec(select(ErrorLog).where(
        ErrorLog.user_id == user.id, ErrorLog.lang == lang)
        .order_by(ErrorLog.created_at.desc()).limit(30)).all()
    cats = Counter(e.category for e in errs)
    weak = ", ".join(f"{k}" for k, _ in cats.most_common(3)) or "general"
    pack = langs.get(lang)
    level = user.level_de if lang == "de" else user.level_en

    try:
        resp = client.messages.parse(
            model=config.ANTHROPIC_MODEL_PRO,
            max_tokens=900,
            system=[{"type": "text", "text":
                f"Eres planificador de estudio de {pack.name_es}. Crea un plan PERSONALIZADO en español "
                f"para un alumno de nivel {level} cuyas debilidades son: {weak}. Objetivos del alumno: "
                f"{user.goals or 'mejorar en general'}."}],
            messages=[{"role": "user", "content":
                "Genera: objectives (lista de metas), weekly_schedule (7 items día/focus/activity), "
                "topics (lista de temas a practicar)."}],
            output_format=StudyContent,
        )
        c = resp.parsed_output.model_dump()
    except Exception:
        c = {
            "objectives": [f"Reforzar {weak}", "Ampliar vocabulario", "Hablar 10 min al día"],
            "weekly_schedule": [{"day": d, "focus": weak, "activity": "Conversación + flashcards"}
                                for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]],
            "topics": ["Vida cotidiana", "Viajes", "Trabajo"],
        }
    c["level"] = level
    return c
