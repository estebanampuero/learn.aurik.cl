"""Tablas SQLModel. Todo el estado por usuario vive aquí.

JSON anidado (items, sinónimos, payloads) se guarda como texto JSON en columnas `*_json`
para mantener el esquema simple y portable entre SQLite y Postgres.
"""
from datetime import datetime, date

from sqlmodel import SQLModel, Field


def _now() -> datetime:
    return datetime.utcnow()


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    name: str = ""
    native_lang: str = "es"
    goals: str = ""                 # objetivos del alumno (texto libre, onboarding)
    level_de: str = "A1"            # nivel auto-estimado por idioma
    level_en: str = "A1"
    created_at: datetime = Field(default_factory=_now)


class Conversation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    lang: str = "de"
    tutor_id: str = "lena"
    mode: str = "chat"             # chat | lesson | roleplay | exam
    scenario_id: str = ""          # id de lección/roleplay/examen si aplica
    title: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(index=True, foreign_key="conversation.id")
    role: str                      # user | assistant
    content: str                   # texto plano (lo que se manda al historial de Claude)
    payload_json: str = ""         # turno completo del tutor (corrección, gramática, vocab, nivel…)
    created_at: datetime = Field(default_factory=_now)


class SavedWord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    lang: str = "de"
    word: str
    pos: str = ""
    ipa: str = ""
    translation_es: str = ""
    synonyms_json: str = "[]"
    example_de: str = ""
    example_es: str = ""
    learned_at: datetime = Field(default_factory=_now)
    source_conversation_id: int | None = None
    # SRS (SM-2 simplificado)
    srs_due: datetime = Field(default_factory=_now)
    srs_interval: int = 0          # días
    srs_ease: float = 2.5
    reps: int = 0


class Flashcard(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    lang: str = "de"
    mode: str = "multiple_choice"  # multiple_choice | fill_blank | reverse
    front: str                     # pregunta / prompt
    back: str                      # respuesta correcta
    options_json: str = "[]"       # opciones (multiple_choice) o vacío
    hint: str = ""
    source: str = "vocab"          # vocab | error | phrase
    created_at: datetime = Field(default_factory=_now)
    # SRS
    srs_due: datetime = Field(default_factory=_now)
    srs_interval: int = 0
    srs_ease: float = 2.5
    reps: int = 0


class ErrorLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    lang: str = "de"
    category: str = "general"      # grammar | vocabulary | spelling | word_order | …
    wrong: str = ""
    right: str = ""
    explanation: str = ""
    created_at: datetime = Field(default_factory=_now)


class PronunciationAttempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    lang: str = "de"
    target: str = ""
    transcript: str = ""
    accuracy: int = 0              # 0-100
    intonation: int = 0
    fluency: int = 0
    overall: int = 0
    tips: str = ""
    created_at: datetime = Field(default_factory=_now)


class ProgressEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    type: str                      # message | conversation | flashcard | pronunciation | lesson | exam
    xp: int = 0
    meta_json: str = "{}"
    created_at: datetime = Field(default_factory=_now)


class Achievement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    code: str                      # first_conversation | words_100 | streak_30 | level_b1 …
    unlocked_at: datetime = Field(default_factory=_now)


class Streak(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    current: int = 0
    longest: int = 0
    last_active_date: date | None = None


class WeeklyReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    week_start: date
    content_json: str = "{}"
    created_at: datetime = Field(default_factory=_now)


class StudyPlan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    content_json: str = "{}"
    active: bool = True
    created_at: datetime = Field(default_factory=_now)


class MemoryFact(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    lang: str = "de"
    kind: str = "note"             # recurring_error | topic | goal | level | note
    content: str = ""
    created_at: datetime = Field(default_factory=_now)
