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
from app.repositories.session_repo import get_session
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


def _parse_connection_cookie_payload(payload: dict[str, Any]) -> tuple[UUID, str]:
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
        return UUID(raw_session_id), raw_cookies
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be a valid UUID",
        ) from exc


def _resolve_session_merchant_domain(
    *,
    db: Session,
    session_id: UUID,
    current_user,
) -> str:
    from app.api.routes.session import _require_existing_session

    _require_existing_session(db, session_id, current_user=current_user)
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session.merchant.value


def _set_connection_cookies(
    *,
    session_id: UUID,
    cookies: str,
    merchant_domain: str,
    browser_client: BrowserRuntimeClient,
) -> dict[str, bool]:
    runtime_setter = getattr(browser_client, "set_connection_cookies", None)
    if callable(runtime_setter):
        try:
            runtime_setter(
                session_id=session_id,
                cookies=cookies,
                merchant_domain=merchant_domain,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to load merchant cookies into the browser runtime: {exc}",
            ) from exc
        return {"connected": True}

    try:
        with httpx.Client(base_url=settings.BROWSER_RUNTIME_BASE_URL, timeout=10.0) as client:
            response = client.post(
                f"/sessions/{session_id}/cookies",
                json={
                    "cookies": cookies,
                    "merchant_domain": merchant_domain,
                },
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


def _get_connection_status_payload(
    *,
    session_id: UUID,
    merchant_domain: str,
    browser_client: BrowserRuntimeClient,
) -> AmazonConnectionStatus:
    runtime_getter = getattr(browser_client, "get_connection_status", None)
    if callable(runtime_getter):
        try:
            payload = runtime_getter(
                session_id=session_id,
                merchant_domain=merchant_domain,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to inspect merchant connection status: {exc}",
            ) from exc
        return AmazonConnectionStatus.model_validate(payload or {})

    try:
        with httpx.Client(base_url=settings.BROWSER_RUNTIME_BASE_URL, timeout=10.0) as client:
            response = client.get(
                f"/sessions/{session_id}/observation/auth_status",
                params={"merchant_domain": merchant_domain},
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach the browser runtime: {exc}",
        ) from exc

    if not response.is_success:
        detail = response.text.strip() or "browser runtime rejected the status request"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="browser runtime returned invalid status JSON",
        ) from exc

    return AmazonConnectionStatus.model_validate(payload or {})


@router.post("/amazon/cookies")
def set_amazon_connection_cookies(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> dict[str, bool]:
    session_id, cookies = _parse_connection_cookie_payload(payload)
    merchant_domain = _resolve_session_merchant_domain(
        db=db,
        session_id=session_id,
        current_user=current_user,
    )
    return _set_connection_cookies(
        session_id=session_id,
        cookies=cookies,
        merchant_domain=merchant_domain,
        browser_client=browser_client,
    )


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
    merchant_domain = _resolve_session_merchant_domain(
        db=db,
        session_id=session_id,
        current_user=current_user,
    )
    return _get_connection_status_payload(
        session_id=session_id,
        merchant_domain=merchant_domain,
        browser_client=browser_client,
    )


@router.post("/bigbasket/cookies")
def set_bigbasket_connection_cookies(
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> dict[str, bool]:
    session_id, cookies = _parse_connection_cookie_payload(payload)
    merchant_domain = _resolve_session_merchant_domain(
        db=db,
        session_id=session_id,
        current_user=current_user,
    )
    return _set_connection_cookies(
        session_id=session_id,
        cookies=cookies,
        merchant_domain=merchant_domain,
        browser_client=browser_client,
    )


@router.get("/bigbasket/status/{session_id}", response_model=AmazonConnectionStatus)
def get_bigbasket_connection_status(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user=Depends(get_current_user_optional),
) -> AmazonConnectionStatus:
    merchant_domain = _resolve_session_merchant_domain(
        db=db,
        session_id=session_id,
        current_user=current_user,
    )
    return _get_connection_status_payload(
        session_id=session_id,
        merchant_domain=merchant_domain,
        browser_client=browser_client,
    )
