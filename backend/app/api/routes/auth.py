"""注册 / 登录。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import StudentProfile, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=4, max_length=64)
    role: str = Field(pattern="^(teacher|student)$")
    display_name: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name or user.username,
    }


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    username = body.username.strip()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(400, "用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(body.password),
        role=body.role,
        display_name=(body.display_name or username).strip(),
    )
    db.add(user)
    db.flush()
    if body.role == "student":
        db.add(StudentProfile(user_id=user.id))
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, role=user.role, username=user.username)
    return {"token": token, "user": _user_out(user)}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username.strip()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token(user_id=user.id, role=user.role, username=user.username)
    return {"token": token, "user": _user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
