from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.db.session import get_db
from app.repositories.session_repo import (
    append_agent_log,
    create_session,
    get_session,
    list_agent_logs_for_session,
    list_sessions,
)
from app.repositories.session_context_repo import get_session_context, update_session_context
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.control_state import CheckpointStatus, SensitiveCheckpointRequest
from app.schemas.purchase_support import FinalPurchaseConfirmation
from app.schemas.session_context import SessionContextSnapshot
from app.schemas.session import Merchant, SessionCreate, SessionDetail, SessionSummary

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


@router.post(
    "",
    response_model=SessionDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_session_endpoint(
    payload: SessionCreate,
    db: Session = Depends(get_db),
) -> SessionDetail:
    return create_session(db, payload)


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
)
def get_session_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> SessionDetail:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
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
) -> list[SessionSummary]:
    items = list_sessions(db, limit=limit, offset=offset)
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
) -> AgentLogEntry:
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
) -> list[AgentLogEntry]:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return list_agent_logs_for_session(db, session_id)


@router.get(
    "/{session_id}/context",
    response_model=SessionContextSnapshot,
)
def get_session_context_endpoint(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> SessionContextSnapshot:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

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
) -> SensitiveCheckpointRequest:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

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
) -> SensitiveCheckpointRequest:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    context = get_session_context(db, session_id)
    if context is None or context.latest_sensitive_checkpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found")

    checkpoint = context.latest_sensitive_checkpoint.model_copy(
        update={
            "status": CheckpointStatus.APPROVED if payload.approved else CheckpointStatus.REJECTED,
            "resolved_at": datetime.utcnow(),
            "resolution_notes": payload.resolution_notes,
        }
    )
    updated_context = update_session_context(
        db,
        session_id,
        latest_sensitive_checkpoint=checkpoint,
        latest_final_purchase_confirmation=FinalPurchaseConfirmation(
            required=True,
            confirmed=payload.approved,
            prompt_to_user=None if payload.approved else "User rejected final purchase confirmation.",
            confirmation_phrase_expected="confirm purchase",
            notes=(
                "Final purchase checkpoint resolved as approved."
                if payload.approved
                else "Final purchase checkpoint resolved as rejected."
            ),
        ),
    )
    if updated_context.latest_sensitive_checkpoint is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Checkpoint update failed")
    return updated_context.latest_sensitive_checkpoint
