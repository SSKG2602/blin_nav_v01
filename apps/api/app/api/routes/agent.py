from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from app.agent.orchestrator import AgentOrchestrator
from app.agent.state import AgentCommand, AgentEvent, AgentState
from app.db.session import get_db

router = APIRouter(prefix="/api/sessions", tags=["agent"])


class AgentStepResponse(BaseModel):
    new_state: AgentState
    spoken_summary: str | None = None
    commands: list[AgentCommand]
    debug_notes: str | None = None


@router.post(
    "/{session_id}/agent/step",
    response_model=AgentStepResponse,
    status_code=status.HTTP_200_OK,
)
def run_agent_step_endpoint(
    session_id: UUID,
    event: AgentEvent,
    db: Session = Depends(get_db),
) -> AgentStepResponse:
    orchestrator = AgentOrchestrator(db)
    try:
        transition = orchestrator.run_step(session_id, event)
    except ValueError as exc:
        if str(exc) == "Session does not exist":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        raise

    return AgentStepResponse(
        new_state=transition.new_state,
        spoken_summary=transition.spoken_summary,
        commands=transition.commands,
        debug_notes=transition.debug_notes,
    )
