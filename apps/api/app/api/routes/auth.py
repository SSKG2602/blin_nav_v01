from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.db.session import get_db
from app.repositories.auth_repo import authenticate_user, create_user, issue_auth_token
from app.schemas.auth import AuthSessionResponse, LoginRequest, SignupRequest
from app.security import get_current_user_required

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup_endpoint(
    payload: SignupRequest,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    try:
        profile = create_user(
            db,
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
            preferred_locale=payload.preferred_locale,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
                if str(exc) == "User already exists"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        )
    token = issue_auth_token(db, user_id=profile.user_id)
    return AuthSessionResponse(token=token, profile=profile)


@router.post(
    "/login",
    response_model=AuthSessionResponse,
)
def login_endpoint(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    try:
        profile = authenticate_user(db, email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = issue_auth_token(db, user_id=profile.user_id)
    return AuthSessionResponse(token=token, profile=profile)


@router.get(
    "/me",
    response_model=AuthSessionResponse,
)
def get_me_endpoint(current_user=Depends(get_current_user_required)) -> AuthSessionResponse:
    return AuthSessionResponse(token=current_user.token, profile=current_user.profile)
