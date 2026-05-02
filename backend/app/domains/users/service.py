from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.users.models import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.scalar(select(User).where(User.id == user_id))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def set_user_admin_status(db: Session, user: User, *, is_admin: bool) -> User:
    user.is_admin = is_admin
    db.add(user)
    db.flush()
    return user
