from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.llm.dependencies import get_llm_client
from app.main import app
from app.models import AgentLogORM, SessionORM
from app.repositories.session_repo import get_session, list_agent_logs_for_session
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.session import Merchant, SessionStatus
from app.tools.dependencies import get_browser_runtime_client


class FakeBrowserRuntimeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def navigate_to_search_results(
        self,
        *,
        session_id: UUID,
        query: str | None,
        merchant: Merchant | None,
    ) -> None:
        self.calls.append(
            {
                "method": "navigate_to_search_results",
                "session_id": session_id,
                "query": query,
                "merchant": merchant,
            }
        )

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
    ) -> None:
        self.calls.append(
            {
                "method": "inspect_product_page",
                "session_id": session_id,
                "page_type": page_type,
            }
        )

    def verify_product_variant(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "verify_product_variant",
                "session_id": session_id,
            }
        )

    def review_cart(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "review_cart",
                "session_id": session_id,
            }
        )

    def perform_checkout(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "perform_checkout",
                "session_id": session_id,
            }
        )

    def handle_error_recovery(
        self,
        *,
        session_id: UUID,
        error_type: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "handle_error_recovery",
                "session_id": session_id,
                "error_type": error_type,
            }
        )

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        return {}


class FakeLLMClient:
    def summarize_page_and_verification(self, page, verification) -> str:
        return "Fallback summary from fake llm."

    def analyze_multimodal_assessment(
        self,
        *,
        intent,
        page,
        verification,
        spoken_summary: str | None = None,
    ) -> MultimodalAssessment:
        return MultimodalAssessment(
            decision=MultimodalDecision.REQUIRE_USER_CONFIRMATION,
            confidence=0.55,
            confidence_band=ConfidenceBand.MEDIUM,
            needs_user_confirmation=True,
            needs_sensitive_checkpoint=False,
            should_halt_low_confidence=False,
            ambiguity_notes=["Test fake multimodal output."],
            trust_notes=["Test context available."],
            review_notes=["Verification pending."],
            reasoning_summary="Need user confirmation in test harness.",
            recommended_next_step="ask_user_confirmation",
            notes="FakeLLMClient multimodal output.",
        )


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
def fake_browser_client() -> FakeBrowserRuntimeClient:
    return FakeBrowserRuntimeClient()


@pytest.fixture
def client(testing_session_local, fake_browser_client: FakeBrowserRuntimeClient) -> TestClient:

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_get_browser_runtime_client() -> FakeBrowserRuntimeClient:
        return fake_browser_client

    def override_get_llm_client() -> FakeLLMClient:
        return FakeLLMClient()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_browser_runtime_client] = override_get_browser_runtime_client
    app.dependency_overrides[get_llm_client] = override_get_llm_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_agent_step_happy_path_multi_step(
    client: TestClient,
    testing_session_local,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
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

    assert [call["method"] for call in fake_browser_client.calls] == [
        "navigate_to_search_results",
        "inspect_product_page",
        "review_cart",
        "perform_checkout",
    ]
    assert fake_browser_client.calls[0]["query"] == "dog food"
    assert fake_browser_client.calls[0]["merchant"] == Merchant.AMAZON

    with testing_session_local() as db:
        logs = list_agent_logs_for_session(db, session_uuid)
        assert len(logs) >= len(steps)

        session = get_session(db, session_uuid)
        assert session is not None
        assert session.status in {SessionStatus.ACTIVE, SessionStatus.ENDED}


def test_agent_step_returns_404_for_missing_session(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
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
    assert fake_browser_client.calls == []


def test_agent_step_low_confidence_path(
    client: TestClient,
    testing_session_local,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
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
    assert fake_browser_client.calls == []

    with testing_session_local() as db:
        logs = list_agent_logs_for_session(db, session_uuid)
        assert logs
        assert any(log.low_confidence is True for log in logs)

        session = get_session(db, session_uuid)
        assert session is not None
        assert session.status == SessionStatus.ERROR


def test_agent_step_tool_error_dispatches_runtime_recovery(
    client: TestClient,
    testing_session_local,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    session_uuid = UUID(session_id)

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "tool_error",
            "error_type": "navigation_error",
            "error_message": "selector lookup failed",
        },
    )

    assert step_response.status_code == 200
    payload = step_response.json()
    assert payload["new_state"] == "ERROR_RECOVERY"
    assert any(command["type"] == "HANDLE_ERROR_RECOVERY" for command in payload["commands"])

    assert len(fake_browser_client.calls) == 1
    assert fake_browser_client.calls[0]["method"] == "handle_error_recovery"
    assert fake_browser_client.calls[0]["error_type"] == "navigation_error"

    with testing_session_local() as db:
        session = get_session(db, session_uuid)
        assert session is not None
        assert session.status == SessionStatus.ERROR
