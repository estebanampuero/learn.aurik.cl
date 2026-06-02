"""XP, rachas y logros. Todo se deriva de eventos guardados (ProgressEvent) + tablas."""
from datetime import date, timedelta

from sqlmodel import Session, select, func

from models import ProgressEvent, Achievement, Streak, SavedWord, Conversation, PronunciationAttempt

# XP por tipo de acción.
XP = {
    "message": 5,
    "conversation": 20,
    "flashcard": 3,
    "pronunciation": 10,
    "lesson": 25,
    "exam": 40,
    "save_word": 2,
}

# Catálogo de logros: code → (emoji, título, descripción, función de condición).
ACHIEVEMENTS = [
    ("first_conversation", "🏆", "Primera conversación", "Completa tu primera conversación"),
    ("words_25", "📒", "25 palabras", "Guarda 25 palabras"),
    ("words_100", "📚", "100 palabras", "Guarda 100 palabras"),
    ("streak_3", "🔥", "Racha de 3 días", "Practica 3 días seguidos"),
    ("streak_7", "🔥", "Racha de 7 días", "Practica 7 días seguidos"),
    ("streak_30", "🔥", "Racha de 30 días", "Practica 30 días seguidos"),
    ("streak_100", "💎", "Racha de 100 días", "Practica 100 días seguidos"),
    ("pronunciation_90", "🎙️", "Pronunciación 90%", "Logra 90% en pronunciación"),
    ("xp_500", "⭐", "500 XP", "Acumula 500 XP"),
    ("xp_2000", "🌟", "2000 XP", "Acumula 2000 XP"),
]


def award(session: Session, user_id: int, kind: str, meta: dict | None = None, xp: int | None = None) -> int:
    """Registra un evento de XP y devuelve el XP otorgado."""
    points = XP.get(kind, 0) if xp is None else xp
    import json
    session.add(ProgressEvent(user_id=user_id, type=kind, xp=points, meta_json=json.dumps(meta or {})))
    return points


def total_xp(session: Session, user_id: int) -> int:
    return session.exec(
        select(func.coalesce(func.sum(ProgressEvent.xp), 0)).where(ProgressEvent.user_id == user_id)
    ).one()


def touch_streak(session: Session, user_id: int) -> Streak:
    """Actualiza la racha según la actividad de hoy. Idempotente por día."""
    streak = session.get(Streak, user_id) or Streak(user_id=user_id)
    today = date.today()
    if streak.last_active_date == today:
        pass  # ya contado hoy
    elif streak.last_active_date == today - timedelta(days=1):
        streak.current += 1
    else:
        streak.current = 1
    streak.last_active_date = today
    streak.longest = max(streak.longest, streak.current)
    session.add(streak)
    return streak


def _unlocked_codes(session: Session, user_id: int) -> set[str]:
    rows = session.exec(select(Achievement.code).where(Achievement.user_id == user_id)).all()
    return set(rows)


def check_achievements(session: Session, user_id: int, level_de: str = "A1", level_en: str = "A1") -> list[dict]:
    """Evalúa condiciones y desbloquea logros nuevos. Devuelve los recién desbloqueados."""
    have = _unlocked_codes(session, user_id)
    words = session.exec(
        select(func.count()).select_from(SavedWord).where(SavedWord.user_id == user_id)
    ).one()
    convs = session.exec(
        select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
    ).one()
    streak = session.get(Streak, user_id)
    cur_streak = streak.current if streak else 0
    best_pron = session.exec(
        select(func.coalesce(func.max(PronunciationAttempt.overall), 0))
        .where(PronunciationAttempt.user_id == user_id)
    ).one()
    xp = total_xp(session, user_id)
    levels = {level_de, level_en}

    conds = {
        "first_conversation": convs >= 1,
        "words_25": words >= 25,
        "words_100": words >= 100,
        "streak_3": cur_streak >= 3,
        "streak_7": cur_streak >= 7,
        "streak_30": cur_streak >= 30,
        "streak_100": cur_streak >= 100,
        "pronunciation_90": best_pron >= 90,
        "xp_500": xp >= 500,
        "xp_2000": xp >= 2000,
        "level_b1": bool(levels & {"B1", "B2", "C1", "C2"}),
        "level_c1": bool(levels & {"C1", "C2"}),
    }
    meta = {c[0]: (c[1], c[2], c[3]) for c in ACHIEVEMENTS}
    meta.setdefault("level_b1", ("🥈", "Nivel B1", "Alcanza el nivel B1"))
    meta.setdefault("level_c1", ("🥇", "Nivel C1", "Alcanza el nivel C1"))

    newly: list[dict] = []
    for code, ok in conds.items():
        if ok and code not in have:
            session.add(Achievement(user_id=user_id, code=code))
            emoji, title, desc = meta.get(code, ("🏅", code, ""))
            newly.append({"code": code, "emoji": emoji, "title": title, "desc": desc})
    return newly


def achievement_catalog() -> list[dict]:
    cat = [{"code": c, "emoji": e, "title": t, "desc": d} for c, e, t, d in ACHIEVEMENTS]
    cat += [
        {"code": "level_b1", "emoji": "🥈", "title": "Nivel B1", "desc": "Alcanza el nivel B1"},
        {"code": "level_c1", "emoji": "🥇", "title": "Nivel C1", "desc": "Alcanza el nivel C1"},
    ]
    return cat
