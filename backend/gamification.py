"""XP, niveles/rangos, rachas, misiones diarias y logros.
Todo se deriva de eventos guardados (ProgressEvent) + tablas. Gamificación ligera."""
import json
from datetime import date, datetime, timedelta

from sqlmodel import Session, select, func

from models import ProgressEvent, Achievement, Streak, SavedWord, Conversation, PronunciationAttempt

# XP por tipo de acción.
XP = {
    "message": 5,
    "conversation": 20,
    "flashcard": 3,
    "pronunciation": 10,
    "lesson": 25,
    "lesson_complete": 50,
    "exam": 60,
    "game": 15,
    "quest": 30,
    "save_word": 2,
}

# ─── Niveles / rangos (derivado del XP total) ─────────────────────────────────
# Umbral acumulado de XP para alcanzar cada nivel: nivel n requiere 100*n*(n-1)/2... usamos
# una curva simple: xp_total para nivel L = 50 * L * (L-1). Rango por tramos de nivel.
RANKS = ["Principiante", "Aprendiz", "Explorador", "Conversador", "Avanzado", "Experto", "Maestro"]


def _xp_for_level(level: int) -> int:
    return 50 * level * (level - 1)   # L1=0, L2=100, L3=300, L4=600, L5=1000…


def level_info(xp: int) -> dict:
    level = 1
    while _xp_for_level(level + 1) <= xp:
        level += 1
    base = _xp_for_level(level)
    nxt = _xp_for_level(level + 1)
    rank = RANKS[min(len(RANKS) - 1, (level - 1) // 3)]
    return {
        "level": level, "rank": rank, "xp": xp,
        "xp_in_level": xp - base, "xp_to_next": nxt - base,
        "next_at": nxt,
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
    ("game_first", "🎮", "Primer juego", "Juega tu primera partida"),
    ("lesson_done", "✅", "Lección completa", "Completa una lección guiada"),
    ("exam_done", "📜", "Primer examen", "Termina un test de nivel"),
    ("level_5", "🚀", "Nivel 5", "Alcanza el nivel 5"),
]

# Misiones diarias (se calculan desde los ProgressEvent de hoy).
DAILY_QUESTS = [
    {"id": "xp_60", "title": "Gana 60 XP hoy", "icon": "⚡", "goal": 60, "metric": "xp"},
    {"id": "talk_1", "title": "Ten una conversación", "icon": "💬", "goal": 1, "metric": "message"},
    {"id": "play_1", "title": "Juega una partida", "icon": "🎮", "goal": 1, "metric": "game"},
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

    def _count_type(t: str) -> int:
        return session.exec(select(func.count()).select_from(ProgressEvent)
                            .where(ProgressEvent.user_id == user_id, ProgressEvent.type == t)).one()

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
        "game_first": _count_type("game") >= 1,
        "lesson_done": _count_type("lesson_complete") >= 1,
        "exam_done": _count_type("exam") >= 1,
        "level_5": level_info(xp)["level"] >= 5,
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


# ─── Misiones diarias ─────────────────────────────────────────────────────────
def daily_quests(session: Session, user_id: int) -> list[dict]:
    """Calcula el progreso de las quests de hoy y otorga bonus único al cumplir."""
    today = date.today()
    start = datetime(today.year, today.month, today.day)
    events = session.exec(select(ProgressEvent).where(
        ProgressEvent.user_id == user_id, ProgressEvent.created_at >= start)).all()

    xp_today = sum(e.xp for e in events)
    counts: dict[str, int] = {}
    claimed: set[str] = set()
    for e in events:
        counts[e.type] = counts.get(e.type, 0) + 1
        if e.type == "quest":
            try:
                m = json.loads(e.meta_json or "{}")
                if m.get("date") == today.isoformat():
                    claimed.add(m.get("id"))
            except Exception:
                pass

    out = []
    for q in DAILY_QUESTS:
        progress = xp_today if q["metric"] == "xp" else counts.get(q["metric"], 0)
        done = progress >= q["goal"]
        # Otorga bonus una vez al cumplir (idempotente por id+fecha).
        if done and q["id"] not in claimed:
            session.add(ProgressEvent(user_id=user_id, type="quest", xp=XP["quest"],
                                      meta_json=json.dumps({"id": q["id"], "date": today.isoformat()})))
            claimed.add(q["id"])
        out.append({**q, "progress": min(progress, q["goal"]), "done": done})
    return out
