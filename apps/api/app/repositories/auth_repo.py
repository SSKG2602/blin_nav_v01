from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session import UserAuthTokenORM, UserORM
from app.schemas.auth import UserProfile

_PASSWORD_ITERATIONS = 120_000


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email(email: str) -> None:
    if "@" not in email or "." not in email.split("@", 1)[-1]:
        raise ValueError("Invalid email address")


def _hash_password(*, password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PASSWORD_ITERATIONS,
    )
    return derived.hex()


def _to_user_profile(row: UserORM) -> UserProfile:
    return UserProfile(
        user_id=UUID(row.id),
        email=row.email,
        display_name=row.display_name,
        preferred_locale=row.preferred_locale,
        created_at=row.created_at,
    )


def create_user(
    db: Session,
    *,
    email: str,
    display_name: str,
    password: str,
    preferred_locale: str | None = None,
) -> UserProfile:
    normalized_email = _normalize_email(email)
    _validate_email(normalized_email)
    existing = db.query(UserORM).filter(UserORM.email == normalized_email).first()
    if existing is not None:
        raise ValueError("User already exists")

    salt = secrets.token_hex(16)
    row = UserORM(
        email=normalized_email,
        display_name=display_name.strip(),
        password_hash=_hash_password(password=password, salt=salt),
        password_salt=salt,
        preferred_locale=preferred_locale.strip() if isinstance(preferred_locale, str) and preferred_locale.strip() else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_user_profile(row)


def authenticate_user(db: Session, *, email: str, password: str) -> UserProfile | None:
    normalized_email = _normalize_email(email)
    _validate_email(normalized_email)
    row = db.query(UserORM).filter(UserORM.email == normalized_email).first()
    if row is None:
        return None
    if _hash_password(password=password, salt=row.password_salt) != row.password_hash:
        return None
    return _to_user_profile(row)


def issue_auth_token(db: Session, *, user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    row = UserAuthTokenORM(
        token=token,
        user_id=str(user_id),
        created_at=now,
        last_used_at=now,
    )
    db.add(row)
    db.commit()
    return token


def get_user_profile(db: Session, *, user_id: UUID) -> UserProfile | None:
    row = db.query(UserORM).filter(UserORM.id == str(user_id)).first()
    if row is None:
        return None
    return _to_user_profile(row)


def get_user_by_token(db: Session, *, token: str) -> UserProfile | None:
    token_row = db.query(UserAuthTokenORM).filter(UserAuthTokenORM.token == token).first()
    if token_row is None:
        return None
    user_row = db.query(UserORM).filter(UserORM.id == token_row.user_id).first()
    if user_row is None:
        return None
    # Hot auth lookups back the demo shell polling endpoints. Avoid per-request writes here
    # so the live path does not exhaust the database pool under observation/screenshot polling.
    return _to_user_profile(user_row)
