from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session import AgentLogORM, SessionORM
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.session import (
    Merchant,
    SessionCreate,
    SessionDetail,
    SessionStatus,
    SessionSummary,
)


def _to_session_detail(row: SessionORM) -> SessionDetail:
    return SessionDetail(
        session_id=UUID(row.id),
        merchant=Merchant(row.merchant),
        status=SessionStatus(row.status),
        created_at=row.created_at,
        locale=row.locale,
        screen_reader=row.screen_reader,
        client_version=row.client_version,
    )


def _to_session_summary(row: SessionORM) -> SessionSummary:
    return SessionSummary(
        session_id=UUID(row.id),
        merchant=Merchant(row.merchant),
        status=SessionStatus(row.status),
        created_at=row.created_at,
    )


def _to_agent_log_entry(row: AgentLogORM) -> AgentLogEntry:
    return AgentLogEntry(
        id=UUID(row.id),
        session_id=UUID(row.session_id),
        step_type=AgentStepType(row.step_type),
        state_before=row.state_before,
        state_after=row.state_after,
        tool_name=row.tool_name,
        tool_input_excerpt=row.tool_input_excerpt,
        tool_output_excerpt=row.tool_output_excerpt,
        low_confidence=row.low_confidence,
        human_checkpoint=row.human_checkpoint,
        user_spoken_summary=row.user_spoken_summary,
        error_type=row.error_type,
        error_message=row.error_message,
        created_at=row.created_at,
    )


def create_session(db: Session, payload: SessionCreate) -> SessionDetail:
    row = SessionORM(
        merchant=payload.merchant.value,
        status=SessionStatus.ACTIVE.value,
        locale=payload.locale,
        screen_reader=payload.screen_reader,
        client_version=payload.client_version,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_session_detail(row)


def get_session(db: Session, session_id: UUID) -> SessionDetail | None:
    row = db.query(SessionORM).filter(SessionORM.id == str(session_id)).first()
    if row is None:
        return None
    return _to_session_detail(row)


def list_sessions(db: Session, limit: int = 20, offset: int = 0) -> list[SessionSummary]:
    rows: Sequence[SessionORM] = (
        db.query(SessionORM)
        .order_by(SessionORM.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_to_session_summary(row) for row in rows]


def append_agent_log(db: Session, entry: AgentLogEntry) -> AgentLogEntry:
    parent = db.query(SessionORM).filter(SessionORM.id == str(entry.session_id)).first()
    if parent is None:
        raise ValueError("Session does not exist")

    row = AgentLogORM(
        id=str(entry.id),
        session_id=str(entry.session_id),
        step_type=entry.step_type.value,
        state_before=entry.state_before,
        state_after=entry.state_after,
        tool_name=entry.tool_name,
        tool_input_excerpt=entry.tool_input_excerpt,
        tool_output_excerpt=entry.tool_output_excerpt,
        low_confidence=entry.low_confidence,
        human_checkpoint=entry.human_checkpoint,
        user_spoken_summary=entry.user_spoken_summary,
        error_type=entry.error_type,
        error_message=entry.error_message,
        created_at=entry.created_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_agent_log_entry(row)


def list_agent_logs_for_session(db: Session, session_id: UUID) -> list[AgentLogEntry]:
    rows: Sequence[AgentLogORM] = (
        db.query(AgentLogORM)
        .filter(AgentLogORM.session_id == str(session_id))
        .order_by(AgentLogORM.created_at.asc())
        .all()
    )
    return [_to_agent_log_entry(row) for row in rows]
