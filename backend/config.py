"""Configuración por variables de entorno."""
import os

# Modelo de Claude para el chat (uso diario, alto volumen). Por defecto Haiku 4.5
# (barato/rápido). Para mejor calidad pedagógica: claude-opus-4-8 o claude-sonnet-4-6.
ANTHROPIC_MODEL = os.getenv("DEUTSCH_TUTOR_MODEL", "claude-haiku-4-5")

# Modelo "Pro" para razonamiento pesado y de baja frecuencia: informe semanal,
# plan de estudio, evaluación de nivel/pronunciación, generación de flashcards.
ANTHROPIC_MODEL_PRO = os.getenv("DEUTSCH_TUTOR_MODEL_PRO", "claude-sonnet-4-6")

# ─── Persistencia (SQLModel/SQLAlchemy). SQLite por defecto, en volumen /data ──
# Swap a Postgres = cambiar DATABASE_URL (ej. postgresql+psycopg://user:pass@host/db).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/app.db")

# ─── Auth (JWT) ───────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "30"))

# ─── STT (Whisper) — reutiliza el que ya tienes en el VPS ───────────────────
# OPCIÓN B (recomendada en VPS): si urgencias-er expone un servicio HTTP de
# transcripción, pon su URL aquí y deutsch-tutor NO carga el modelo: le pega por
# HTTP (una sola copia de Whisper en RAM para todas las apps).
STT_SERVICE_URL = os.getenv("STT_SERVICE_URL", "")   # ej. http://urgencias-er:5050/api/v1/transcribe
STT_SERVICE_TOKEN = os.getenv("STT_SERVICE_TOKEN", "")  # Bearer (= STT_INTERNAL_TOKEN de urgencias-er)
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "de")

# OPCIÓN A: si cargas el modelo localmente, apunta al MISMO caché ya descargado
# para no volver a bajar los pesos (compártelo con urgencias-er/transportesmoreira).
# Debe ser el modelo MULTILINGÜE (no '.en'); sirve para alemán y español.
WHISPER_SIZE = os.getenv("WHISPER_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")
WHISPER_DOWNLOAD_ROOT = os.getenv("WHISPER_DOWNLOAD_ROOT", "") or None  # caché compartido

# Voz Piper (alemán). Los archivos .onnx + .onnx.json se descargan en el Dockerfile.
PIPER_MODEL = os.getenv("PIPER_MODEL", "/app/voices/de_DE-thorsten-medium.onnx")
