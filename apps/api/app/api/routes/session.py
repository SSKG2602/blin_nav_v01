from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.agent.observation import build_page_understanding_from_browser_observation
from app.agent.order_support import build_latest_order_snapshot
from app.agent.orchestrator import AgentOrchestrator
from app.agent.runtime_bridge import build_cart_snapshot
from app.agent.state import AgentState, HumanCheckpointResolved
from app.db.session import get_db
from app.llm.client import BlindNavLLMClient
from app.llm.dependencies import get_llm_client
from app.repositories.session_repo import (
    append_agent_log,
    create_session,
    get_session,
    list_agent_logs_for_session,
    list_sessions,
)
from app.repositories.session_context_repo import get_session_context, update_session_context
from app.security import AuthenticatedUser, get_current_user_optional
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.cart_context import CartSnapshot
from app.schemas.control_state import CheckpointStatus, SensitiveCheckpointRequest
from app.schemas.order_support import LatestOrderSnapshot, OrderCancellationResult
from app.schemas.purchase_support import FinalPurchaseConfirmation
from app.schemas.session_context import SessionContextSnapshot
from app.schemas.session import Merchant, SessionCreate, SessionDetail, SessionSummary
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.dependencies import get_browser_runtime_client

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class AgentLogCreate(BaseModel):
    step_type: AgentStepType
    state_before: str | None = None
    state_after: str | None = None
    tool_name: str | None = None
    tool_input_excerpt: str | None = None
    tool_output_excerpt: str | None = None
    low_confidence: bool = False
    human_checkpoint: bool = False
    user_spoken_summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None


class CheckpointResolveRequest(BaseModel):
    approved: bool
    resolution_notes: str | None = None


class FinalConfirmationResolveRequest(BaseModel):
    approved: bool
    resolution_notes: str | None = None


class RemoveCartItemRequest(BaseModel):
    item_id: str | None = None
    title: str | None = None


class UpdateCartQuantityRequest(BaseModel):
    item_id: str | None = None
    title: str | None = None
    quantity: int


def _require_existing_session(
    db: Session,
    session_id: UUID,
    *,
    current_user: AuthenticatedUser | None = None,
) -> None:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if (
        current_user is not None
        and session.user_id is not None
        and session.user_id != current_user.profile.user_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session access denied")


def resolve_sensitive_checkpoint_state(
    db: Session,
    session_id: UUID,
    *,
    approved: bool,
    resolution_notes: str | None = None,
) -> SensitiveCheckpointRequest:
    _require_existing_session(db, session_id)

    context = get_session_context(db, session_id)
    if context is None or context.latest_sensitive_checkpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")

    checkpoint = context.latest_sensitive_checkpoint.model_copy(
        update={
            "status": CheckpointStatus.APPROVED if approved else CheckpointStatus.REJECTED,
            "resolved_at": datetime.utcnow(),
            "resolution_notes": resolution_notes,
        }
    )
    updated_context = update_session_context(
        db,
        session_id,
        latest_sensitive_checkpoint=checkpoint,
    )
    if updated_context.latest_sensitive_checkpoint is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Checkpoint update failed",
        )
    return updated_context.latest_sensitive_checkpoint


def resolve_final_purchase_confirmation_state(
    db: Session,
    session_id: UUID,
    *,
    approved: bool,
    resolution_notes: str | None = None,
) -> FinalPurchaseConfirmation:
    _require_existing_session(db, session_id)

    context = get_session_context(db, session_id)
    existing_confirmation = (
        context.latest_final_purchase_confirmation if context is not None else None
    )
    if existing_confirmation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Final confirmation not found",
        )

    updated_checkpoint = None
    if (
        context is not None
        and context.latest_sensitive_checkpoint is not None
        and context.latest_sensitive_checkpoint.status == CheckpointStatus.PENDING
    ):
        updated_checkpoint = context.latest_sensitive_checkpoint.model_copy(
            update={
                "status": CheckpointStatus.APPROVED if approved else CheckpointStatus.REJECTED,
                "resolved_at": datetime.utcnow(),
                "resolution_notes": resolution_notes,
            }
        )

    updated_confirmation = existing_confirmation.model_copy(
        update={
            "required": True,
            "confirmed": approved,
            "prompt_to_user": (
                None if approved else "Final purchase confirmation was rejected."
            ),
            "notes": resolution_notes
            or ("Final confirmation approved." if approved else "Final confirmation rejected."),
        }
    )

    updated_context = update_session_context(
        db,
        session_id,
        latest_sensitive_checkpoint=updated_checkpoint,
        latest_final_purchase_confirmation=updated_confirmation,
    )
    if updated_context.latest_final_purchase_confirmation is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Final confirmation update failed",
    )
    return updated_context.latest_final_purchase_confirmation


def _resume_after_control_resolution(
    *,
    db: Session,
    session_id: UUID,
    approved: bool,
    browser_client: BrowserRuntimeClient,
    llm_client: BlindNavLLMClient,
    expected_states: set[AgentState],
) -> None:
    orchestrator = AgentOrchestrator(db)
    current_state = orchestrator._infer_current_state(session_id)
    if current_state not in expected_states:
        return

    from app.api.routes.agent import run_agent_step_endpoint

    run_agent_step_endpoint(
        session_id=session_id,
        event=HumanCheckpointResolved(approved=approved),
        db=db,
        browser_client=browser_client,
        llm_client=llm_client,
    )


def _refresh_runtime_context(
    *,
    db: Session,
    session_id: UUID,
    browser_client: BrowserRuntimeClient,
) -> SessionContextSnapshot:
    context = get_session_context(db, session_id)
    raw_observation = browser_client.get_current_page_observation(session_id=session_id)
    if not isinstance(raw_observation, dict):
        raw_observation = {}

    page_understanding = build_page_understanding_from_browser_observation(raw_observation)
    cart_snapshot = build_cart_snapshot(
        page=page_understanding,
        observation=raw_observation,
        previous_snapshot=context.latest_cart_snapshot if context is not None else None,
    )
    order_snapshot = build_latest_order_snapshot(raw_observation)
    return update_session_context(
        db,
        session_id,
        latest_page_understanding=page_understanding,
        latest_cart_snapshot=cart_snapshot,
        latest_order_snapshot=order_snapshot,
    )


@router.post(
    "",
    response_model=SessionDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_session_endpoint(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> SessionDetail:
    locale = payload.locale
    if locale is None and current_user is not None:
        locale = current_user.profile.preferred_locale
    return create_session(
        db,
        payload.model_copy(update={"locale": locale}),
        user_id=current_user.profile.user_id if current_user is not None else None,
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
)
def get_session_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> SessionDetail:
    _require_existing_session(db, session_id, current_user=current_user)
    session = get_session(db, session_id)
    assert session is not None
    return session


@router.get(
    "",
    response_model=list[SessionSummary],
)
def list_sessions_endpoint(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    merchant: Merchant | None = None,
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> list[SessionSummary]:
    items = list_sessions(
        db,
        limit=limit,
        offset=offset,
        user_id=current_user.profile.user_id if current_user is not None else None,
    )
    if merchant is None:
        return items
    return [item for item in items if item.merchant == merchant]


@router.post(
    "/{session_id}/logs",
    response_model=AgentLogEntry,
    status_code=status.HTTP_201_CREATED,
)
def append_agent_log_endpoint(
    session_id: UUID,
    payload: AgentLogCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> AgentLogEntry:
    _require_existing_session(db, session_id, current_user=current_user)
    entry = AgentLogEntry(session_id=session_id, **payload.model_dump())
    try:
        return append_agent_log(db, entry)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.get(
    "/{session_id}/logs",
    response_model=list[AgentLogEntry],
)
def list_agent_logs_for_session_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> list[AgentLogEntry]:
    _require_existing_session(db, session_id, current_user=current_user)
    return list_agent_logs_for_session(db, session_id)


@router.get(
    "/{session_id}/context",
    response_model=SessionContextSnapshot,
)
def get_session_context_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> SessionContextSnapshot:
    _require_existing_session(db, session_id, current_user=current_user)

    context = get_session_context(db, session_id)
    if context is not None:
        return context

    return SessionContextSnapshot(session_id=session_id)


@router.get(
    "/{session_id}/checkpoint",
    response_model=SensitiveCheckpointRequest,
)
def get_session_checkpoint_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> SensitiveCheckpointRequest:
    _require_existing_session(db, session_id, current_user=current_user)

    context = get_session_context(db, session_id)
    if context is None or context.latest_sensitive_checkpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")
    return context.latest_sensitive_checkpoint


@router.post(
    "/{session_id}/checkpoint/resolve",
    response_model=SensitiveCheckpointRequest,
)
def resolve_session_checkpoint_endpoint(
    session_id: UUID,
    payload: CheckpointResolveRequest,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    llm_client: BlindNavLLMClient = Depends(get_llm_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> SensitiveCheckpointRequest:
    _require_existing_session(db, session_id, current_user=current_user)
    resolved = resolve_sensitive_checkpoint_state(
        db,
        session_id,
        approved=payload.approved,
        resolution_notes=payload.resolution_notes,
    )
    _resume_after_control_resolution(
        db=db,
        session_id=session_id,
        approved=payload.approved,
        browser_client=browser_client,
        llm_client=llm_client,
        expected_states={AgentState.CHECKPOINT_SENSITIVE_ACTION},
    )
    return resolved


@router.get(
    "/{session_id}/final-confirmation",
    response_model=FinalPurchaseConfirmation,
)
def get_final_purchase_confirmation_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> FinalPurchaseConfirmation:
    _require_existing_session(db, session_id, current_user=current_user)

    context = get_session_context(db, session_id)
    if context is None or context.latest_final_purchase_confirmation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Final confirmation not found",
        )
    return context.latest_final_purchase_confirmation


@router.post(
    "/{session_id}/final-confirmation/resolve",
    response_model=FinalPurchaseConfirmation,
)
def resolve_final_purchase_confirmation_endpoint(
    session_id: UUID,
    payload: FinalConfirmationResolveRequest,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    llm_client: BlindNavLLMClient = Depends(get_llm_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> FinalPurchaseConfirmation:
    _require_existing_session(db, session_id, current_user=current_user)
    resolved = resolve_final_purchase_confirmation_state(
        db,
        session_id,
        approved=payload.approved,
        resolution_notes=payload.resolution_notes,
    )
    _resume_after_control_resolution(
        db=db,
        session_id=session_id,
        approved=payload.approved,
        browser_client=browser_client,
        llm_client=llm_client,
        expected_states={AgentState.FINAL_CONFIRMATION},
    )
    return resolved


@router.post(
    "/{session_id}/cart/remove",
    response_model=CartSnapshot,
)
def remove_cart_item_endpoint(
    session_id: UUID,
    payload: RemoveCartItemRequest,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> CartSnapshot:
    _require_existing_session(db, session_id, current_user=current_user)
    browser_client.remove_cart_item(
        session_id=session_id,
        item_id=payload.item_id,
        title=payload.title,
    )
    refreshed = _refresh_runtime_context(
        db=db,
        session_id=session_id,
        browser_client=browser_client,
    )
    if refreshed.latest_cart_snapshot is None:
        return CartSnapshot(items=[], cart_item_count=0, checkout_ready=None, notes="Cart snapshot unavailable.")
    return refreshed.latest_cart_snapshot


@router.post(
    "/{session_id}/cart/quantity",
    response_model=CartSnapshot,
)
def update_cart_quantity_endpoint(
    session_id: UUID,
    payload: UpdateCartQuantityRequest,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> CartSnapshot:
    _require_existing_session(db, session_id, current_user=current_user)
    browser_client.update_cart_quantity(
        session_id=session_id,
        item_id=payload.item_id,
        title=payload.title,
        quantity=payload.quantity,
    )
    refreshed = _refresh_runtime_context(
        db=db,
        session_id=session_id,
        browser_client=browser_client,
    )
    if refreshed.latest_cart_snapshot is None:
        return CartSnapshot(items=[], cart_item_count=0, checkout_ready=None, notes="Cart snapshot unavailable.")
    return refreshed.latest_cart_snapshot


@router.post(
    "/{session_id}/orders/latest",
    response_model=LatestOrderSnapshot,
)
def load_latest_order_snapshot_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> LatestOrderSnapshot:
    _require_existing_session(db, session_id, current_user=current_user)
    browser_client.navigate_orders_history(session_id=session_id)
    refreshed = _refresh_runtime_context(
        db=db,
        session_id=session_id,
        browser_client=browser_client,
    )
    if refreshed.latest_order_snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Latest order snapshot not available",
        )
    return refreshed.latest_order_snapshot


@router.post(
    "/{session_id}/orders/cancel",
    response_model=OrderCancellationResult,
)
def cancel_latest_order_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> OrderCancellationResult:
    _require_existing_session(db, session_id, current_user=current_user)
    payload = browser_client.cancel_latest_order(session_id=session_id)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Browser runtime did not return an order cancellation result",
        )

    try:
        result = OrderCancellationResult.model_validate(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid order cancellation payload: {exc}",
        ) from exc

    _refresh_runtime_context(
        db=db,
        session_id=session_id,
        browser_client=browser_client,
    )
    return result


@router.get(
    "/{session_id}/orders/latest",
    response_model=LatestOrderSnapshot,
)
def get_latest_order_snapshot_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> LatestOrderSnapshot:
    _require_existing_session(db, session_id, current_user=current_user)
    context = get_session_context(db, session_id)
    if context is None or context.latest_order_snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Latest order snapshot not found",
        )
    return context.latest_order_snapshot


@router.get(
    "/{session_id}/runtime/observation",
    response_model=dict[str, object],
)
def get_runtime_observation_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    _require_existing_session(db, session_id, current_user=current_user)
    payload = browser_client.get_current_page_observation(session_id=session_id)
    return payload if isinstance(payload, dict) else {}


@router.get(
    "/{session_id}/runtime/screenshot",
    response_model=dict[str, object],
)
def get_runtime_screenshot_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    _require_existing_session(db, session_id, current_user=current_user)
    payload = browser_client.get_current_page_screenshot(session_id=session_id)
    return payload if isinstance(payload, dict) else {}
