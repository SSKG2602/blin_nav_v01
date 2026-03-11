from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.engine import next_state
from app.agent.state import AgentEvent, AgentState, AgentTransitionResult
from app.models.session import SessionORM
from app.repositories.session_repo import append_agent_log, get_session, list_agent_logs_for_session
from app.schemas.session import SessionStatus


class AgentOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    def _infer_current_state(self, session_id: UUID) -> AgentState:
        logs = list_agent_logs_for_session(self.db, session_id)
        if not logs:
            return AgentState.SESSION_INITIALIZING

        for latest in reversed(logs):
            if not latest.state_after:
                continue
            try:
                return AgentState(latest.state_after)
            except ValueError:
                continue
        return AgentState.SESSION_INITIALIZING

    def _sync_session_status(self, session_id: UUID, new_state: AgentState) -> None:
        row = self.db.query(SessionORM).filter(SessionORM.id == str(session_id)).first()
        if row is None:
            return

        if new_state in {
            AgentState.ORDER_PLACED,
            AgentState.POST_PURCHASE_SUMMARY,
            AgentState.SESSION_CLOSING,
            AgentState.DONE,
        }:
            row.status = SessionStatus.ENDED.value
        elif new_state in {AgentState.ERROR_RECOVERY, AgentState.LOW_CONFIDENCE_HALT}:
            row.status = SessionStatus.ERROR.value
        else:
            row.status = SessionStatus.ACTIVE.value

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

    def run_step(self, session_id: UUID, event: AgentEvent) -> AgentTransitionResult:
        session = get_session(self.db, session_id)
        if session is None:
            raise ValueError("Session does not exist")

        current_state = self._infer_current_state(session_id)
        transition = next_state(current_state=current_state, event=event, session_id=session_id)

        for log_entry in transition.log_entries:
            append_agent_log(self.db, log_entry)

        self._sync_session_status(session_id, transition.new_state)
        return transition
