from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AgentLogORM, SessionORM
from app.repositories.session_repo import get_session, list_agent_logs_for_session
from app.schemas.session import SessionStatus


@pytest.fixture
def testing_session_local():
    assert SessionORM is not None
    assert AgentLogORM is not None

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    yield session_local
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(testing_session_local) -> TestClient:

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_agent_step_happy_path_multi_step(client: TestClient, testing_session_local) -> None:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    session_uuid = UUID(session_id)

    steps = [
        (
            {
                "event_type": "user_intent_parsed",
                "intent": "search_products",
                "query": "dog food",
                "merchant": "amazon.in",
            },
            "SEARCHING_PRODUCTS",
            "NAVIGATE_TO_SEARCH_RESULTS",
        ),
        (
            {
                "event_type": "nav_result",
                "success": True,
                "confidence": 0.9,
                "page_type": "search_results",
            },
            "VIEWING_PRODUCT_DETAIL",
            "INSPECT_PRODUCT_PAGE",
        ),
        (
            {
                "event_type": "verification_result",
                "success": True,
            },
            "CART_VERIFICATION",
            "REVIEW_CART",
        ),
        (
            {
                "event_type": "checkout_progress",
                "proceed_to_checkout": True,
            },
            "CHECKOUT_FLOW",
            "PERFORM_CHECKOUT",
        ),
    ]

    for payload, expected_state, expected_command in steps:
        response = client.post(f"/api/sessions/{session_id}/agent/step", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["new_state"] == expected_state
        assert data["spoken_summary"]
        assert data["commands"]
        assert any(command["type"] == expected_command for command in data["commands"])

    with testing_session_local() as db:
        logs = list_agent_logs_for_session(db, session_uuid)
        assert len(logs) >= len(steps)

        session = get_session(db, session_uuid)
        assert session is not None
        assert session.status in {SessionStatus.ACTIVE, SessionStatus.ENDED}


def test_agent_step_returns_404_for_missing_session(client: TestClient) -> None:
    missing_session_id = uuid4()
    response = client.post(
        f"/api/sessions/{missing_session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_agent_step_low_confidence_path(client: TestClient, testing_session_local) -> None:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    session_uuid = UUID(session_id)

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "low_confidence_triggered",
            "reason": "unsafe ambiguity",
        },
    )

    assert step_response.status_code == 200
    payload = step_response.json()
    assert payload["new_state"] == "LOW_CONFIDENCE_HALT"
    assert any(command["type"] == "HALT_LOW_CONFIDENCE" for command in payload["commands"])

    with testing_session_local() as db:
        logs = list_agent_logs_for_session(db, session_uuid)
        assert logs
        assert any(log.low_confidence is True for log in logs)

        session = get_session(db, session_uuid)
        assert session is not None
        assert session.status == SessionStatus.ERROR
