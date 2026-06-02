"""Autenticación: registro, login, JWT bearer y dependencia current_user."""
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

import config
from db import get_session
from models import User, Streak

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─── modelos de request/response ──────────────────────────────────────────────
class RegisterReq(BaseModel):
    email: EmailStr
    password: str
    name: str = ""
    goals: str = ""


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class AuthResp(BaseModel):
    token: str
    user: dict


# ─── helpers ──────────────────────────────────────────────────────────────────
def hash_password(p: str) -> str:
    # bcrypt limita a 72 bytes; truncamos explícitamente (práctica estándar).
    return bcrypt.hashpw(p.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode("utf-8")[:72], h.encode("utf-8"))
    except Exception:
        return False


def make_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=config.JWT_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALG)


def user_public(u: User) -> dict:
    return {
        "id": u.id, "email": u.email, "name": u.name,
        "goals": u.goals, "level_de": u.level_de, "level_en": u.level_en,
    }


def current_user(
    authorization: str = Header(default=""),
    session: Session = Depends(get_session),
) -> User:
    """Dependencia: extrae el usuario del Bearer token o 401."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Falta token de autenticación.")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALG])
        uid = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Token inválido o expirado.")
    user = session.get(User, uid)
    if not user:
        raise HTTPException(401, "Usuario no encontrado.")
    return user


# ─── endpoints ────────────────────────────────────────────────────────────────
@router.post("/register", response_model=AuthResp)
def register(req: RegisterReq, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == req.email.lower())).first()
    if existing:
        raise HTTPException(400, "Ese email ya está registrado.")
    if len(req.password) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres.")
    user = User(
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        name=req.name.strip(),
        goals=req.goals.strip(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(Streak(user_id=user.id))
    session.commit()
    return AuthResp(token=make_token(user.id), user=user_public(user))


@router.post("/login", response_model=AuthResp)
def login(req: LoginReq, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == req.email.lower())).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Email o contraseña incorrectos.")
    return AuthResp(token=make_token(user.id), user=user_public(user))


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_public(user)
