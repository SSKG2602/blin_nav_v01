from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import AgentLogORM, SessionORM


@pytest.fixture
def client() -> TestClient:
    # Ensure ORM models are registered for metadata creation.
    assert SessionORM is not None
    assert AgentLogORM is not None

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )

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
    Base.metadata.drop_all(bind=engine)


def test_create_and_get_session(client: TestClient) -> None:
    create_response = client.post(
        "/api/sessions",
        json={
            "merchant": "amazon.in",
            "locale": "en-IN",
            "screen_reader": "VoiceOver",
            "client_version": "0.1.0",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["merchant"] == "amazon.in"
    assert created["status"] == "active"
    assert created["session_id"]
    assert created["created_at"]

    get_response = client.get(f"/api/sessions/{created['session_id']}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["session_id"] == created["session_id"]
    assert fetched["merchant"] == "amazon.in"


def test_list_sessions_returns_created_items(client: TestClient) -> None:
    first = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    second = client.post("/api/sessions", json={"merchant": "flipkart.com"}).json()

    list_response = client.get("/api/sessions")
    assert list_response.status_code == 200
    items = list_response.json()
    ids = {item["session_id"] for item in items}
    assert first["session_id"] in ids
    assert second["session_id"] in ids

    filtered_response = client.get("/api/sessions", params={"merchant": "flipkart.com"})
    assert filtered_response.status_code == 200
    filtered = filtered_response.json()
    assert len(filtered) >= 1
    assert all(item["merchant"] == "flipkart.com" for item in filtered)


def test_append_and_list_agent_logs(client: TestClient) -> None:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]

    append_response = client.post(
        f"/api/sessions/{session_id}/logs",
        json={
            "step_type": "navigation",
            "state_before": "SEARCH",
            "state_after": "PRODUCT",
            "tool_name": "playwright.navigate",
            "tool_input_excerpt": "Open first product",
            "tool_output_excerpt": "Navigated to product page",
            "low_confidence": False,
            "human_checkpoint": True,
        },
    )
    assert append_response.status_code == 201
    created_log = append_response.json()
    assert created_log["session_id"] == session_id
    assert created_log["step_type"] == "navigation"
    assert created_log["id"]
    assert created_log["created_at"]

    list_response = client.get(f"/api/sessions/{session_id}/logs")
    assert list_response.status_code == 200
    logs = list_response.json()
    assert len(logs) == 1
    assert logs[0]["session_id"] == session_id
    assert logs[0]["step_type"] == "navigation"


def test_missing_session_returns_404_for_get_and_append_log(client: TestClient) -> None:
    missing_session_id = uuid4()

    get_response = client.get(f"/api/sessions/{missing_session_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Session not found"

    append_response = client.post(
        f"/api/sessions/{missing_session_id}/logs",
        json={"step_type": "navigation"},
    )
    assert append_response.status_code == 404
    assert append_response.json()["detail"] == "Session not found"
