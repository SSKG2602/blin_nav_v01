from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.db.session import get_db
from app.repositories.auth_repo import authenticate_user, create_user, issue_auth_token
from app.schemas.auth import AmazonConnectionStatus, AuthSessionResponse, LoginRequest, SignupRequest
from app.security import get_current_user_optional, get_current_user_required
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.dependencies import get_browser_runtime_client

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


@router.get("/amazon/login")
def amazon_login_redirect() -> RedirectResponse:
    return RedirectResponse(
        url="https://www.amazon.in/ap/signin",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.post("/amazon/cookies")
def set_amazon_connection_cookies(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> dict[str, bool]:
    raw_session_id = payload.get("session_id")
    raw_cookies = payload.get("cookies")

    if not isinstance(raw_session_id, str) or not raw_session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required",
        )
    if not isinstance(raw_cookies, str) or not raw_cookies.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cookies is required",
        )

    try:
        session_id = UUID(raw_session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be a valid UUID",
        ) from exc

    from app.api.routes.session import _require_existing_session

    _require_existing_session(db, session_id, current_user=current_user)

    runtime_setter = getattr(browser_client, "set_amazon_cookies", None)
    if callable(runtime_setter):
        try:
            runtime_setter(session_id=session_id, cookies=raw_cookies)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to load Amazon cookies into the browser runtime: {exc}",
            ) from exc
        return {"connected": True}

    try:
        with httpx.Client(base_url=settings.BROWSER_RUNTIME_BASE_URL, timeout=10.0) as client:
            response = client.post(
                f"/sessions/{session_id}/cookies",
                json={"cookies": raw_cookies},
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach the browser runtime: {exc}",
        ) from exc

    if not response.is_success:
        detail = response.text.strip() or "browser runtime rejected the cookie payload"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    return {"connected": True}


@router.get(
    "/amazon/status/{session_id}",
    response_model=AmazonConnectionStatus,
)
def get_amazon_connection_status(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> AmazonConnectionStatus:
    from app.api.routes.session import _require_existing_session

    _require_existing_session(db, session_id, current_user=current_user)
    payload = browser_client.get_amazon_auth_status(session_id=session_id)
    return AmazonConnectionStatus.model_validate(payload or {})


@router.post("/bigbasket/cookies")
def set_bigbasket_connection_cookies(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> dict[str, bool]:
    """BigBasket cookie loader — same cookie mechanism as Amazon route."""
    return set_amazon_connection_cookies(
        payload=payload, db=db, browser_client=browser_client, current_user=current_user
    )


@router.get("/bigbasket/status/{session_id}", response_model=AmazonConnectionStatus)
def get_bigbasket_connection_status(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> AmazonConnectionStatus:
    return get_amazon_connection_status(
        session_id=session_id, db=db, browser_client=browser_client, current_user=current_user
    )
