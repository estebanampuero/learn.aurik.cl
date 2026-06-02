"""Capa de persistencia (SQLModel/SQLAlchemy). SQLite por defecto en /data/app.db."""
import os
from collections.abc import Iterator

from sqlmodel import SQLModel, Session, create_engine

import config

# Para SQLite hace falta check_same_thread=False (FastAPI usa varios hilos).
_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

# Si es SQLite por archivo, asegura que el directorio exista (ej. /data).
if config.DATABASE_URL.startswith("sqlite:///") and ":memory:" not in config.DATABASE_URL:
    _path = config.DATABASE_URL.split("sqlite:///", 1)[1]  # ej. "/data/app.db"
    _dir = os.path.dirname(_path)
    if _dir:
        os.makedirs(_dir, exist_ok=True)

engine = create_engine(config.DATABASE_URL, echo=False, connect_args=_connect_args)


def init_db() -> None:
    """Crea las tablas si no existen. Se llama al arrancar la app."""
    import models  # noqa: F401  (registra los modelos en SQLModel.metadata)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: una sesión por request."""
    with Session(engine) as session:
        yield session
