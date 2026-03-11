from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.repositories.session_repo import (
    append_agent_log,
    create_session,
    get_session,
    list_agent_logs_for_session,
    list_sessions,
)
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.session import Merchant, SessionCreate, SessionStatus


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with testing_session_local() as session:
        yield session


def test_create_and_get_session_round_trip(db_session: Session) -> None:
    created = create_session(
        db_session,
        SessionCreate(
            merchant=Merchant.DEMO_STORE,
            locale="en-IN",
            screen_reader="VoiceOver",
            client_version="0.1.0",
        ),
    )

    fetched = get_session(db_session, created.session_id)

    assert fetched is not None
    assert fetched.session_id == created.session_id
    assert fetched.merchant == Merchant.DEMO_STORE
    assert fetched.status == SessionStatus.ACTIVE
    assert isinstance(fetched.session_id, UUID)
    assert fetched.created_at is not None


def test_list_sessions_orders_by_created_at(db_session: Session) -> None:
    s1 = create_session(db_session, SessionCreate(merchant=Merchant.DEMO_STORE))
    s2 = create_session(db_session, SessionCreate(merchant=Merchant.FLIPKART))
    s3 = create_session(db_session, SessionCreate(merchant=Merchant.MEESHO))

    items = list_sessions(db_session)

    assert len(items) == 3
    assert items[0].created_at >= items[1].created_at >= items[2].created_at
    returned_ids = {item.session_id for item in items}
    assert returned_ids == {s1.session_id, s2.session_id, s3.session_id}


def test_append_and_list_agent_logs(db_session: Session) -> None:
    created = create_session(db_session, SessionCreate(merchant=Merchant.DEMO_STORE))
    entry = AgentLogEntry(
        session_id=created.session_id,
        step_type=AgentStepType.NAVIGATION,
        low_confidence=True,
        human_checkpoint=True,
        tool_name="playwright.navigate",
        tool_input_excerpt="Open product page",
        tool_output_excerpt="Product page opened",
    )

    persisted = append_agent_log(db_session, entry)
    logs = list_agent_logs_for_session(db_session, created.session_id)

    assert isinstance(persisted.id, UUID)
    assert persisted.created_at is not None
    assert len(logs) == 1
    assert logs[0].session_id == created.session_id
    assert logs[0].step_type == AgentStepType.NAVIGATION
    assert isinstance(logs[0].id, UUID)
    assert logs[0].created_at is not None
