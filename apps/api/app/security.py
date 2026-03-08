from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, WebSocket, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.auth_repo import get_user_by_token
from app.schemas.auth import UserProfile


@dataclass
class AuthenticatedUser:
    profile: UserProfile
    token: str


def _extract_token(
    authorization: str | None,
    x_blindnav_auth: str | None,
) -> str | None:
    if isinstance(authorization, str):
        prefix = "bearer "
        lowered = authorization.lower()
        if lowered.startswith(prefix):
            token = authorization[len(prefix):].strip()
            if token:
                return token
    if isinstance(x_blindnav_auth, str) and x_blindnav_auth.strip():
        return x_blindnav_auth.strip()
    return None


def get_current_user_optional(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_blindnav_auth: str | None = Header(default=None, alias="X-BlindNav-Auth"),
) -> AuthenticatedUser | None:
    token = _extract_token(authorization, x_blindnav_auth)
    if token is None:
        return None
    profile = get_user_by_token(db, token=token)
    if profile is None:
        return None
    return AuthenticatedUser(profile=profile, token=token)


def get_current_user_required(
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> AuthenticatedUser:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


def get_websocket_authenticated_user(
    *,
    db: Session,
    websocket: WebSocket,
) -> AuthenticatedUser | None:
    token = websocket.query_params.get("token")
    if token is None:
        authorization = websocket.headers.get("authorization")
        token = _extract_token(authorization, websocket.headers.get("x-blindnav-auth"))
    if token is None:
        return None
    profile = get_user_by_token(db, token=token)
    if profile is None:
        return None
    return AuthenticatedUser(profile=profile, token=token)
