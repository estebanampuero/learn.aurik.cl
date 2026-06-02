"""API FastAPI: orquesta auth + persistencia + STT → tutor (Claude) → TTS + todas las
funciones de aprendizaje (vocabulario, flashcards, pronunciación, lecciones, roleplay,
examen, progreso, gamificación, informes, memoria)."""
import base64
import json
import os
import tempfile
import time
from datetime import datetime

from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select, func

import langs
import tutors
import scenarios
import memory
import gamification as gam
import pronunciation as pron
import reports
import stt
import tts
import tutor as tutor_mod
from db import get_session, init_db
from auth import router as auth_router, current_user
from models import (User, Conversation, Message, SavedWord, Flashcard, ErrorLog,
                    PronunciationAttempt, Achievement, Streak, WeeklyReport, StudyPlan)

app = FastAPI(title="Sona — Language Tutor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# ════════════════════════ Catálogos (públicos) ════════════════════════════════
@app.get("/api/langs")
def list_langs():
    return {
        "default": langs.DEFAULT,
        "langs": [
            {"code": p.code, "label": p.label, "flag": p.flag, "name_es": p.name_es,
             "tutor": p.tutor, "glyph": p.glyph, "greeting": p.greeting,
             "voices": sorted(p.voices.keys())}
            for p in langs.LANGS.values()
        ],
    }


@app.get("/api/tutors")
def list_tutors(lang: str = ""):
    items = tutors.for_lang(lang) if lang else tutors.TUTORS
    return {"tutors": [tutors.public(t) for t in items]}


@app.get("/api/lessons")
def list_lessons():
    return {"lessons": [scenarios.public(s) for s in scenarios.LESSONS]}


@app.get("/api/roleplays")
def list_roleplays():
    return {"roleplays": [scenarios.public(s) for s in scenarios.ROLEPLAYS]}


@app.get("/api/exams")
def list_exams():
    return {"exams": [scenarios.public(s) for s in scenarios.EXAMS]}


# ════════════════════════ Diccionario / traducción ════════════════════════════
class WordReq(BaseModel):
    word: str
    context: str = ""
    lang: str = "de"


@app.post("/api/word")
def word(req: WordReq, user: User = Depends(current_user)):
    info = tutor_mod.word_info(req.word.strip(), req.context, req.lang)
    return info.model_dump()


class TranslateReq(BaseModel):
    text: str
    mode: str = "message"   # word | phrase | message
    lang: str = "de"


@app.post("/api/translate")
def translate(req: TranslateReq, user: User = Depends(current_user)):
    t = tutor_mod.translate(req.text.strip(), req.mode, req.lang)
    return t.model_dump()


# ════════════════════════ Conversaciones ══════════════════════════════════════
class StartConvReq(BaseModel):
    lang: str = "de"
    tutor_id: str = ""
    mode: str = "chat"       # chat | lesson | roleplay | exam
    scenario_id: str = ""


def _own_conversation(session: Session, user: User, conv_id: int) -> Conversation:
    conv = session.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(404, "Conversación no encontrada.")
    return conv


@app.post("/api/conversations")
def start_conversation(req: StartConvReq, user: User = Depends(current_user),
                       session: Session = Depends(get_session)):
    t = tutors.get(req.tutor_id, req.lang)
    sc = scenarios.get(req.scenario_id)
    pack = langs.get(req.lang)
    title = (sc.title if sc else "Conversación") + f" · {t.name}"
    conv = Conversation(user_id=user.id, lang=req.lang, tutor_id=t.id,
                        mode=req.mode, scenario_id=(sc.id if sc else ""), title=title)
    session.add(conv)
    session.commit()
    session.refresh(conv)
    # Saludo inicial persistido (conversación continua + historial).
    greeting = pack.greeting
    session.add(Message(conversation_id=conv.id, role="assistant", content=greeting,
                        payload_json=json.dumps({"reply": greeting, "tutor_id": t.id})))
    session.commit()
    return {"id": conv.id, "lang": conv.lang, "tutor": tutors.public(t),
            "mode": conv.mode, "scenario_id": conv.scenario_id, "title": conv.title,
            "greeting": greeting}


@app.get("/api/conversations")
def list_conversations(user: User = Depends(current_user), session: Session = Depends(get_session)):
    convs = session.exec(select(Conversation).where(Conversation.user_id == user.id)
                         .order_by(Conversation.updated_at.desc()).limit(50)).all()
    return {"conversations": [
        {"id": c.id, "lang": c.lang, "tutor_id": c.tutor_id, "mode": c.mode,
         "scenario_id": c.scenario_id, "title": c.title,
         "updated_at": c.updated_at.isoformat()} for c in convs]}


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: int, user: User = Depends(current_user),
                     session: Session = Depends(get_session)):
    conv = _own_conversation(session, user, conv_id)
    msgs = session.exec(select(Message).where(Message.conversation_id == conv_id)
                        .order_by(Message.created_at)).all()
    t = tutors.get(conv.tutor_id, conv.lang)
    return {
        "id": conv.id, "lang": conv.lang, "tutor": tutors.public(t), "mode": conv.mode,
        "scenario_id": conv.scenario_id, "title": conv.title,
        "messages": [{"role": m.role, "content": m.content,
                      "payload": json.loads(m.payload_json) if m.payload_json else None}
                     for m in msgs],
    }


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: int, user: User = Depends(current_user),
                        session: Session = Depends(get_session)):
    conv = _own_conversation(session, user, conv_id)
    for m in session.exec(select(Message).where(Message.conversation_id == conv_id)).all():
        session.delete(m)
    session.delete(conv)
    session.commit()
    return {"ok": True}


# ════════════════════════ Chat (núcleo) ═══════════════════════════════════════
def _build_extra_system(session: Session, user: User, conv: Conversation) -> str:
    t = tutors.get(conv.tutor_id, conv.lang)
    blocks = [tutors.persona_line(t)]
    sc = scenarios.get(conv.scenario_id)
    if sc:
        blocks.append("CONTEXTO DE LA SESIÓN: " + sc.prompt)
    mem = memory.build_block(session, user, conv.lang)
    if mem:
        blocks.append(mem)
    return "\n\n".join(blocks)


@app.post("/api/chat")
async def chat(
    conversation_id: int = Form(...),
    audio: UploadFile | None = File(None),
    text: str = Form(""),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    conv = _own_conversation(session, user, conversation_id)
    pack = langs.get(conv.lang)
    t = tutors.get(conv.tutor_id, conv.lang)

    # Historial desde la DB.
    prev = session.exec(select(Message).where(Message.conversation_id == conv.id)
                        .order_by(Message.created_at)).all()
    hist = [{"role": m.role, "content": m.content} for m in prev]

    # 1) Entrada: texto (fallback) o audio (STT).
    t0 = time.monotonic()
    text = (text or "").strip()
    if text:
        user_text = text
    elif audio is not None:
        data = await audio.read()
        suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(data)
            audio_path = f.name
        try:
            user_text = stt.transcribe(audio_path, pack.stt)
        finally:
            os.remove(audio_path)
    else:
        raise HTTPException(400, "Envía audio o texto.")
    if not user_text:
        return {"error": "No se entendió el audio. Intenta de nuevo."}

    # 2) Tutor (Claude) con persona + escenario + memoria.
    hist.append({"role": "user", "content": user_text})
    extra = _build_extra_system(session, user, conv)
    result = tutor_mod.tutor(hist, conv.lang, extra)

    # 3) Persistir mensajes.
    session.add(Message(conversation_id=conv.id, role="user", content=user_text,
                        payload_json=json.dumps({"input": "text" if text else "audio"})))
    payload = result.model_dump()
    session.add(Message(conversation_id=conv.id, role="assistant", content=result.reply,
                        payload_json=json.dumps(payload, ensure_ascii=False)))
    conv.updated_at = datetime.utcnow()
    session.add(conv)

    # 4) Memoria (errores) + nivel auto.
    memory.record_errors(session, user.id, conv.lang,
                         [c.model_dump() for c in result.correction_items], result.explanation_es)
    if result.level_estimate in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        if conv.lang == "de":
            user.level_de = result.level_estimate
        else:
            user.level_en = result.level_estimate
        session.add(user)

    # 5) Gamificación.
    xp = gam.award(session, user.id, "message")
    streak = gam.touch_streak(session, user.id)
    new_ach = gam.check_achievements(session, user.id, user.level_de, user.level_en)
    session.commit()

    # 6) TTS con la voz del tutor.
    audio_bytes = tts.synthesize(result.reply, langs.voice_path(conv.lang, t.gender))
    print(f"[CHAT u{user.id} c{conv.id}] {(time.monotonic()-t0)*1000:.0f}ms reply={result.reply[:50]!r}", flush=True)

    return {
        "user_text": user_text,
        **payload,
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "xp": xp, "streak": streak.current, "new_achievements": new_ach,
        "level": user.level_de if conv.lang == "de" else user.level_en,
    }


# ════════════════════════ Vocabulario (⭐) ═════════════════════════════════════
class SaveWordReq(BaseModel):
    lang: str = "de"
    word: str
    pos: str = ""
    ipa: str = ""
    translation_es: str = ""
    synonyms: list[str] = []
    example_de: str = ""
    example_es: str = ""
    source_conversation_id: int | None = None


@app.post("/api/vocab")
def save_word(req: SaveWordReq, user: User = Depends(current_user), session: Session = Depends(get_session)):
    existing = session.exec(select(SavedWord).where(
        SavedWord.user_id == user.id, SavedWord.lang == req.lang,
        func.lower(SavedWord.word) == req.word.lower())).first()
    if existing:
        return {"saved": False, "reason": "ya_guardada", "id": existing.id}
    w = SavedWord(user_id=user.id, lang=req.lang, word=req.word, pos=req.pos, ipa=req.ipa,
                  translation_es=req.translation_es, synonyms_json=json.dumps(req.synonyms),
                  example_de=req.example_de, example_es=req.example_es,
                  source_conversation_id=req.source_conversation_id)
    session.add(w)
    gam.award(session, user.id, "save_word")
    new_ach = gam.check_achievements(session, user.id, user.level_de, user.level_en)
    session.commit()
    session.refresh(w)
    return {"saved": True, "id": w.id, "new_achievements": new_ach}


@app.get("/api/vocab")
def list_vocab(lang: str = "", user: User = Depends(current_user), session: Session = Depends(get_session)):
    q = select(SavedWord).where(SavedWord.user_id == user.id)
    if lang:
        q = q.where(SavedWord.lang == lang)
    rows = session.exec(q.order_by(SavedWord.learned_at.desc())).all()
    return {"vocab": [
        {"id": w.id, "lang": w.lang, "word": w.word, "pos": w.pos, "ipa": w.ipa,
         "translation_es": w.translation_es, "synonyms": json.loads(w.synonyms_json or "[]"),
         "example_de": w.example_de, "example_es": w.example_es,
         "learned_at": w.learned_at.isoformat()} for w in rows]}


@app.delete("/api/vocab/{word_id}")
def delete_word(word_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    w = session.get(SavedWord, word_id)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "Palabra no encontrada.")
    session.delete(w)
    session.commit()
    return {"ok": True}


# ════════════════════════ Flashcards ══════════════════════════════════════════
@app.post("/api/flashcards/generate")
def generate_flashcards(lang: str = "de", user: User = Depends(current_user),
                        session: Session = Depends(get_session)):
    words = session.exec(select(SavedWord).where(
        SavedWord.user_id == user.id, SavedWord.lang == lang)
        .order_by(SavedWord.learned_at.desc()).limit(20)).all()
    errors = session.exec(select(ErrorLog).where(
        ErrorLog.user_id == user.id, ErrorLog.lang == lang)
        .order_by(ErrorLog.created_at.desc()).limit(12)).all()
    if not words and not errors:
        raise HTTPException(400, "Guarda palabras o conversa para generar flashcards.")
    cards = tutor_mod.generate_flashcards(
        [{"word": w.word, "translation_es": w.translation_es} for w in words],
        [{"wrong": e.wrong, "right": e.right} for e in errors], lang)
    created = []
    for c in cards:
        fc = Flashcard(user_id=user.id, lang=lang, mode=c.mode, front=c.front, back=c.back,
                       options_json=json.dumps(c.options), hint=c.hint)
        session.add(fc)
        session.commit()
        session.refresh(fc)
        created.append(fc.id)
    return {"generated": len(created)}


@app.get("/api/flashcards")
def list_flashcards(lang: str = "", user: User = Depends(current_user), session: Session = Depends(get_session)):
    q = select(Flashcard).where(Flashcard.user_id == user.id, Flashcard.srs_due <= datetime.utcnow())
    if lang:
        q = q.where(Flashcard.lang == lang)
    rows = session.exec(q.order_by(Flashcard.srs_due).limit(40)).all()
    return {"flashcards": [
        {"id": f.id, "lang": f.lang, "mode": f.mode, "front": f.front, "back": f.back,
         "options": json.loads(f.options_json or "[]"), "hint": f.hint} for f in rows]}


class ReviewReq(BaseModel):
    correct: bool


@app.post("/api/flashcards/{card_id}/review")
def review_flashcard(card_id: int, req: ReviewReq, user: User = Depends(current_user),
                     session: Session = Depends(get_session)):
    f = session.get(Flashcard, card_id)
    if not f or f.user_id != user.id:
        raise HTTPException(404, "Tarjeta no encontrada.")
    # SRS SM-2 simplificado.
    from datetime import timedelta
    if req.correct:
        f.reps += 1
        f.srs_interval = 1 if f.reps == 1 else (6 if f.reps == 2 else round(f.srs_interval * f.srs_ease))
        f.srs_ease = min(2.8, f.srs_ease + 0.1)
    else:
        f.reps = 0
        f.srs_interval = 1
        f.srs_ease = max(1.3, f.srs_ease - 0.2)
    f.srs_due = datetime.utcnow() + timedelta(days=f.srs_interval)
    session.add(f)
    xp = gam.award(session, user.id, "flashcard")
    session.commit()
    return {"ok": True, "next_due_days": f.srs_interval, "xp": xp}


# ════════════════════════ Pronunciación ═══════════════════════════════════════
@app.post("/api/pronunciation")
async def pronunciation(
    target: str = Form(...),
    lang: str = Form("de"),
    duration: float = Form(0.0),
    audio: UploadFile = File(...),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    pack = langs.get(lang)
    data = await audio.read()
    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        path = f.name
    try:
        transcript = stt.transcribe(path, pack.stt)
    finally:
        os.remove(path)
    res = pron.score(target, transcript, duration, lang)
    session.add(PronunciationAttempt(
        user_id=user.id, lang=lang, target=target, transcript=transcript,
        accuracy=res["accuracy"], intonation=res["intonation"], fluency=res["fluency"],
        overall=res["overall"], tips=res["tips"]))
    xp = gam.award(session, user.id, "pronunciation")
    new_ach = gam.check_achievements(session, user.id, user.level_de, user.level_en)
    session.commit()
    res["xp"] = xp
    res["new_achievements"] = new_ach
    return res


# ════════════════════════ Progreso / estadísticas ═════════════════════════════
@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), session: Session = Depends(get_session)):
    n_user_msgs = session.exec(select(func.count()).select_from(Message).join(Conversation).where(
        Conversation.user_id == user.id, Message.role == "user")).one()
    n_convs = session.exec(select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user.id)).one()
    n_words = session.exec(select(func.count()).select_from(SavedWord).where(
        SavedWord.user_id == user.id)).one()
    avg_pron = session.exec(select(func.coalesce(func.avg(PronunciationAttempt.overall), 0)).where(
        PronunciationAttempt.user_id == user.id)).one()
    streak = session.get(Streak, user.id)
    xp = gam.total_xp(session, user.id)
    return {
        "hours_studied": round(int(n_user_msgs) * 1.0 / 60, 1),  # estimación (~1 min/mensaje)
        "conversations": int(n_convs),
        "words_learned": int(n_words),
        "avg_pronunciation": round(float(avg_pron)),
        "level_de": user.level_de, "level_en": user.level_en,
        "streak": streak.current if streak else 0,
        "longest_streak": streak.longest if streak else 0,
        "xp": int(xp),
    }


@app.get("/api/stats")
def stats(lang: str = "de", user: User = Depends(current_user), session: Session = Depends(get_session)):
    from collections import Counter
    errs = session.exec(select(ErrorLog).where(
        ErrorLog.user_id == user.id, ErrorLog.lang == lang)).all()
    n_words = session.exec(select(func.count()).select_from(SavedWord).where(
        SavedWord.user_id == user.id, SavedWord.lang == lang)).one()
    avg_pron = session.exec(select(func.coalesce(func.avg(PronunciationAttempt.overall), 0)).where(
        PronunciationAttempt.user_id == user.id, PronunciationAttempt.lang == lang)).one()
    n_voice = session.exec(select(func.count()).select_from(Message).join(Conversation).where(
        Conversation.user_id == user.id, Conversation.lang == lang, Message.role == "user")).one()

    cats = Counter(e.category for e in errs)
    grammar_pen = min(60, cats.get("grammar", 0) * 5 + cats.get("word_order", 0) * 5)
    # Puntajes heurísticos (0-100).
    skills = {
        "Gramática": max(20, 100 - grammar_pen),
        "Vocabulario": min(100, 40 + int(n_words) * 2),
        "Pronunciación": round(float(avg_pron)) or 50,
        "Fluidez": min(100, 45 + int(n_voice) * 2),
        "Comprensión": min(100, 50 + int(n_voice)),
    }
    items = [{"skill": k, "score": v} for k, v in skills.items()]
    strengths = [i for i in items if i["score"] >= 70]
    weaknesses = [i for i in items if i["score"] < 70]
    return {"skills": items, "strengths": strengths, "weaknesses": weaknesses,
            "frequent_error_categories": [{"category": k, "count": v} for k, v in cats.most_common(5)]}


@app.get("/api/achievements")
def achievements(user: User = Depends(current_user), session: Session = Depends(get_session)):
    unlocked = {a.code: a.unlocked_at.isoformat()
                for a in session.exec(select(Achievement).where(Achievement.user_id == user.id)).all()}
    cat = gam.achievement_catalog()
    return {"achievements": [
        {**c, "unlocked": c["code"] in unlocked, "unlocked_at": unlocked.get(c["code"])}
        for c in cat]}


@app.get("/api/streak")
def get_streak(user: User = Depends(current_user), session: Session = Depends(get_session)):
    s = session.get(Streak, user.id)
    return {"current": s.current if s else 0, "longest": s.longest if s else 0,
            "last_active": s.last_active_date.isoformat() if s and s.last_active_date else None}


# ════════════════════════ Premium: plan + informe ═════════════════════════════
@app.post("/api/study-plan")
def make_study_plan(lang: str = "de", user: User = Depends(current_user),
                    session: Session = Depends(get_session)):
    content = reports.study_plan(session, user, lang)
    for old in session.exec(select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.active)).all():
        old.active = False
        session.add(old)
    sp = StudyPlan(user_id=user.id, content_json=json.dumps(content, ensure_ascii=False), active=True)
    session.add(sp)
    session.commit()
    return {"plan": content}


@app.get("/api/study-plan")
def get_study_plan(user: User = Depends(current_user), session: Session = Depends(get_session)):
    sp = session.exec(select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.active)
                      .order_by(StudyPlan.created_at.desc())).first()
    return {"plan": json.loads(sp.content_json) if sp else None}


@app.post("/api/report/weekly")
def make_weekly_report(lang: str = "de", user: User = Depends(current_user),
                       session: Session = Depends(get_session)):
    from datetime import date, timedelta
    content = reports.weekly_report(session, user, lang)
    week_start = date.today() - timedelta(days=date.today().weekday())
    wr = WeeklyReport(user_id=user.id, week_start=week_start,
                      content_json=json.dumps(content, ensure_ascii=False))
    session.add(wr)
    session.commit()
    return {"report": content}


@app.get("/api/reports")
def list_reports(user: User = Depends(current_user), session: Session = Depends(get_session)):
    rows = session.exec(select(WeeklyReport).where(WeeklyReport.user_id == user.id)
                        .order_by(WeeklyReport.created_at.desc()).limit(12)).all()
    return {"reports": [
        {"id": r.id, "week_start": r.week_start.isoformat(),
         "content": json.loads(r.content_json), "created_at": r.created_at.isoformat()}
        for r in rows]}
