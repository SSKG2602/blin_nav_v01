from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agent.orchestrator import AgentOrchestrator
from app.agent.state import (
    AgentState,
    CheckoutProgress,
    HumanCheckpointResolved,
    LowConfidenceTriggered,
    NavResult,
    SessionCloseRequested,
    UserIntentParsed,
    VerificationResult,
)
from app.db.base import Base
from app.repositories.session_repo import create_session, get_session, list_agent_logs_for_session
from app.schemas.session import Merchant, SessionCreate, SessionStatus


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with testing_session_local() as session:
        yield session


def test_orchestrator_progresses_happy_path(db_session: Session) -> None:
    session = create_session(db_session, SessionCreate(merchant=Merchant.AMAZON))
    orchestrator = AgentOrchestrator(db_session)

    steps = [
        UserIntentParsed(query="dog food", merchant=Merchant.AMAZON),
        NavResult(success=True, confidence=0.9, page_type="search_results"),
        VerificationResult(success=True),
        CheckoutProgress(proceed_to_checkout=True),
        CheckoutProgress(sensitive_step_required=True),
        HumanCheckpointResolved(approved=True),
        CheckoutProgress(completed=True),
        SessionCloseRequested(),
    ]

    final_state = None
    for event in steps:
        transition = orchestrator.run_step(session.session_id, event)
        final_state = transition.new_state

    assert final_state == AgentState.DONE

    persisted_logs = list_agent_logs_for_session(db_session, session.session_id)
    assert len(persisted_logs) == len(steps)
    assert persisted_logs[-1].state_after == AgentState.DONE.value

    refreshed = get_session(db_session, session.session_id)
    assert refreshed is not None
    assert refreshed.status == SessionStatus.ENDED


def test_orchestrator_raises_for_missing_session(db_session: Session) -> None:
    orchestrator = AgentOrchestrator(db_session)

    with pytest.raises(ValueError, match="Session does not exist"):
        orchestrator.run_step(uuid4(), UserIntentParsed(query="rice"))


def test_orchestrator_low_confidence_marks_session_error(db_session: Session) -> None:
    session = create_session(db_session, SessionCreate(merchant=Merchant.AMAZON))
    orchestrator = AgentOrchestrator(db_session)

    transition = orchestrator.run_step(
        session.session_id,
        LowConfidenceTriggered(reason="unsafe ambiguity"),
    )

    assert transition.new_state == AgentState.LOW_CONFIDENCE_HALT
    persisted_logs = list_agent_logs_for_session(db_session, session.session_id)
    assert len(persisted_logs) == 1
    assert persisted_logs[0].low_confidence is True
    assert persisted_logs[0].state_after == AgentState.LOW_CONFIDENCE_HALT.value

    refreshed = get_session(db_session, session.session_id)
    assert refreshed is not None
    assert refreshed.status == SessionStatus.ERROR
