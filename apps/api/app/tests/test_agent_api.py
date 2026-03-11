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
        self.stage = "home"
        self.search_observation_override: dict[str, Any] | None = None
        self.product_observation_override: dict[str, Any] | None = None

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
        self.stage = "search"

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
        candidate_url: str | None = None,
        candidate_title: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "inspect_product_page",
                "session_id": session_id,
                "page_type": page_type,
                "candidate_url": candidate_url,
                "candidate_title": candidate_title,
            }
        )
        self.stage = "product"

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "verify_product_variant",
                "session_id": session_id,
                "variant_hint": variant_hint,
                "size_hint": size_hint,
                "color_hint": color_hint,
            }
        )

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "select_product_variant",
                "session_id": session_id,
                "variant_hint": variant_hint,
                "size_hint": size_hint,
                "color_hint": color_hint,
            }
        )

    def add_to_cart(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "add_to_cart",
                "session_id": session_id,
            }
        )
        self.stage = "cart"

    def review_cart(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "review_cart",
                "session_id": session_id,
            }
        )
        self.stage = "cart"

    def perform_checkout(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "perform_checkout",
                "session_id": session_id,
            }
        )
        self.stage = "checkout"

    def finalize_purchase(self, *, session_id: UUID) -> None:
        self.calls.append(
            {
                "method": "finalize_purchase",
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
        if self.stage == "search":
            if self.search_observation_override is not None:
                return dict(self.search_observation_override)
            return {
                "observed_url": "https://demo.nopcommerce.com/search?q=htc",
                "page_title": "Search",
                "detected_page_hints": ["search_results"],
                "product_candidates": [
                    {
                        "title": "Nokia Lumia 1020",
                        "price_text": "$349.00",
                        "url": "https://demo.nopcommerce.com/nokia-lumia-1020",
                    },
                    {
                        "title": "HTC One M8 Android L 5.0 Lollipop",
                        "price_text": "$245.00",
                        "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                        "rating_text": "4.4 out of 5 stars",
                        "review_count_text": "1234 reviews",
                        "summary_text": "Android smartphone",
                    },
                ],
            }
        if self.stage == "product":
            if self.product_observation_override is not None:
                return dict(self.product_observation_override)
            return {
                "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                "page_title": "HTC One M8 Android L 5.0 Lollipop",
                "detected_page_hints": ["product_detail"],
                "primary_product": {
                    "title": "HTC One M8 Android L 5.0 Lollipop",
                    "price_text": "$245.00",
                    "summary_text": "Android smartphone",
                    "quantity_text": "Qty: 1",
                    "rating_text": "4.4 out of 5 stars",
                    "review_count_text": "1234 reviews",
                },
            }
        if self.stage == "cart":
            return {
                "observed_url": "https://demo.nopcommerce.com/cart",
                "page_title": "Shopping cart",
                "detected_page_hints": ["cart"],
                "cart_item_count": 1,
                "checkout_ready": True,
                "cart_items": [
                    {
                        "item_id": "item-1",
                        "title": "HTC One M8 Android L 5.0 Lollipop",
                        "price_text": "$245.00",
                        "quantity_text": "1",
                    }
                ],
                "primary_product": {
                    "title": "HTC One M8 Android L 5.0 Lollipop",
                    "price_text": "$245.00",
                },
            }
        if self.stage == "checkout":
            return {
                "observed_url": "https://demo.nopcommerce.com/login/checkoutasguest",
                "page_title": "Welcome, Please Sign In!",
                "detected_page_hints": ["checkout", "guest_checkout_entry_visible"],
                "checkout_ready": True,
                "primary_product": {
                    "title": "HTC One M8 Android L 5.0 Lollipop",
                    "price_text": "$245.00",
                },
                "notes": "guest_checkout_entry_visible",
            }
        return {"observed_url": "https://demo.nopcommerce.com", "page_title": "nopCommerce demo store"}

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        return {}


class FakeLLMClient:
    def __init__(self) -> None:
        self.multimodal_decision = MultimodalDecision.PROCEED

    def score_product_candidates(self, *, query, candidates): return None

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
        decision = self.multimodal_decision
        confidence = 0.22 if decision == MultimodalDecision.HALT_LOW_CONFIDENCE else 0.55
        confidence_band = (
            ConfidenceBand.LOW if decision == MultimodalDecision.HALT_LOW_CONFIDENCE else ConfidenceBand.MEDIUM
        )
        return MultimodalAssessment(
            decision=decision,
            confidence=confidence,
            confidence_band=confidence_band,
            needs_user_confirmation=decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
            needs_sensitive_checkpoint=decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
            should_halt_low_confidence=decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
            ambiguity_notes=["Test fake multimodal output."],
            trust_notes=["Test context available."],
            review_notes=["Verification pending."],
            reasoning_summary=f"FakeLLMClient decision: {decision.value}",
            recommended_next_step="continue",
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


def test_agent_step_closes_happy_path_from_single_user_intent(
    client: TestClient,
    testing_session_local,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]
    session_uuid = UUID(session_id)

    response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "one m8",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_state"] == "FINAL_CONFIRMATION"
    assert (
        data["spoken_summary"]
        == "Checkout entry reached for HTC One M8 Android L 5.0 Lollipop. Stopping before guest checkout."
    )
    assert [
        command["type"] for command in data["commands"]
    ] == [
        "RUN_TRUST_CHECK",
        "NAVIGATE_TO_SEARCH_RESULTS",
        "INSPECT_PRODUCT_PAGE",
        "SELECT_PRODUCT_VARIANT",
        "ANALYZE_REVIEWS",
        "ADD_TO_CART",
        "REVIEW_CART",
        "PERFORM_CHECKOUT",
        "REQUEST_FINAL_CONFIRMATION",
    ]

    assert [call["method"] for call in fake_browser_client.calls] == [
        "navigate_to_search_results",
        "inspect_product_page",
        "select_product_variant",
        "add_to_cart",
        "review_cart",
        "perform_checkout",
    ]
    assert fake_browser_client.calls[0]["query"] == "one m8"
    assert fake_browser_client.calls[0]["merchant"] == Merchant.DEMO_STORE
    assert (
        fake_browser_client.calls[1]["candidate_url"]
        == "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop"
    )
    assert fake_browser_client.calls[2]["size_hint"] is None
    assert not any(call["method"] == "finalize_purchase" for call in fake_browser_client.calls)

    with testing_session_local() as db:
        logs = list_agent_logs_for_session(db, session_uuid)
        assert len(logs) >= 5
        audit_logs = [log for log in logs if log.tool_name == "agent.audit"]
        assert audit_logs
        assert any(log.tool_input_excerpt and "page=SEARCH_RESULTS" in log.tool_input_excerpt for log in audit_logs)
        assert any(log.tool_output_excerpt and "verification=MATCH" in log.tool_output_excerpt for log in audit_logs)
        assert any(
            log.tool_output_excerpt and "checkout_stop=guest_checkout_entry_visible" in log.tool_output_excerpt
            for log in audit_logs
        )
        assert any(
            log.user_spoken_summary == "Results loaded. I found 2 candidates on the demo store."
            for log in audit_logs
        )
        assert any(
            log.user_spoken_summary == "Checkout entry reached for HTC One M8 Android L 5.0 Lollipop. Stopping before guest checkout."
            for log in audit_logs
        )

        session = get_session(db, session_uuid)
        assert session is not None
        assert session.status in {SessionStatus.ACTIVE, SessionStatus.ENDED}


def test_agent_step_requests_product_selection_clarification_for_similar_candidates(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    fake_browser_client.search_observation_override = {
        "observed_url": "https://demo.nopcommerce.com/search?q=htc+one",
        "page_title": "Search",
        "detected_page_hints": ["search_results"],
        "product_candidates": [
            {
                "title": "HTC One Mini Blue",
                "price_text": "$189.00",
                "url": "https://demo.nopcommerce.com/htc-one-mini-blue",
                "rating_text": "4.4 out of 5 stars",
                "review_count_text": "812 reviews",
            },
            {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
                "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                "rating_text": "4.5 out of 5 stars",
                "review_count_text": "1024 reviews",
            },
        ],
    }

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc one",
            "merchant": "demo.nopcommerce.com",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["new_state"] == "CLARIFICATION_REQUIRED"
    assert [call["method"] for call in fake_browser_client.calls] == ["navigate_to_search_results"]

    context = client.get(f"/api/sessions/{session_id}/context").json()
    clarification = context["latest_clarification_request"]
    assert clarification["kind"] == "PRODUCT_SELECTION"
    assert len(clarification["candidate_options"]) == 2
    candidate_urls = {option["candidate_url"] for option in clarification["candidate_options"]}
    assert candidate_urls == {
        "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        "https://demo.nopcommerce.com/htc-one-mini-blue",
    }
    assert any(option.get("difference_summary") for option in clarification["candidate_options"])


def test_agent_step_approved_product_selection_opens_bound_candidate(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    fake_browser_client.search_observation_override = {
        "observed_url": "https://demo.nopcommerce.com/search?q=htc+one",
        "page_title": "Search",
        "detected_page_hints": ["search_results"],
        "product_candidates": [
            {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
                "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                "rating_text": "4.5 out of 5 stars",
                "review_count_text": "1024 reviews",
            },
            {
                "title": "HTC One Mini Blue",
                "price_text": "$189.00",
                "url": "https://demo.nopcommerce.com/htc-one-mini-blue",
                "rating_text": "4.4 out of 5 stars",
                "review_count_text": "812 reviews",
            },
        ],
    }
    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    first = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc one",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert first.status_code == 200
    assert first.json()["new_state"] == "CLARIFICATION_REQUIRED"
    clarification = client.get(f"/api/sessions/{session_id}/context").json()["latest_clarification_request"]
    selected_option = clarification["candidate_options"][0]
    fake_browser_client.product_observation_override = {
        "observed_url": selected_option["candidate_url"],
        "page_title": selected_option["title"],
        "detected_page_hints": ["product_detail"],
        "primary_product": {
            "title": selected_option["title"],
            "price_text": selected_option["price_text"],
            "rating_text": "4.6 out of 5 stars",
            "review_count_text": "1450 reviews",
            "quantity_text": "Qty: 1",
            "review_snippets": [
                "Battery life feels solid for a demo phone fixture.",
                "Most buyers say the screen looks bright and clear.",
            ],
        },
    }

    second = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "clarification_resolved",
            "approved": True,
            "resume_state": "SEARCHING_PRODUCTS",
        },
    )
    assert second.status_code == 200
    follow_up = second.json()
    assert any(command["type"] == "INSPECT_PRODUCT_PAGE" for command in follow_up["commands"])
    assert follow_up["new_state"] in {"VIEWING_PRODUCT_DETAIL", "REVIEW_ANALYSIS", "CLARIFICATION_REQUIRED", "FINAL_CONFIRMATION"}

    inspect_calls = [call for call in fake_browser_client.calls if call["method"] == "inspect_product_page"]
    assert inspect_calls
    assert inspect_calls[0]["candidate_url"] == selected_option["candidate_url"]


def test_agent_step_runtime_blocker_requests_clarification_before_add_to_cart(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    fake_browser_client.search_observation_override = {
        "observed_url": "https://demo.nopcommerce.com/search?q=build+your+own+computer",
        "page_title": "Search",
        "detected_page_hints": ["search_results"],
        "product_candidates": [
            {
                "title": "Build your own computer",
                "price_text": "$1,200.00",
                "url": "https://demo.nopcommerce.com/build-your-own-computer",
                "summary_text": "Desktop computer demo fixture",
            },
        ],
    }
    fake_browser_client.product_observation_override = {
        "observed_url": "https://demo.nopcommerce.com/build-your-own-computer",
        "page_title": "Build your own computer",
        "detected_page_hints": ["product_detail", "option_selection_required"],
        "primary_product": {
            "title": "Build your own computer",
            "price_text": "$1,200.00",
            "summary_text": "Desktop computer demo fixture",
            "variant_options": ["Processor *", "RAM *"],
        },
        "notes": "option_selection_required, required_options:Processor *; RAM *",
    }

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "build your own computer",
            "merchant": "demo.nopcommerce.com",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["new_state"] == "CLARIFICATION_REQUIRED"
    assert (
        payload["spoken_summary"]
        == "Product blocked before add to cart. Build your own computer still needs required options selected."
    )
    assert [call["method"] for call in fake_browser_client.calls] == [
        "navigate_to_search_results",
        "inspect_product_page",
        "select_product_variant",
    ]

    context = client.get(f"/api/sessions/{session_id}/context").json()
    assert context["latest_clarification_request"]["kind"] == "VARIANT_PRECISION"
    assert "option_selection_required" in context["latest_page_understanding"]["detected_page_hints"]


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
    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
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
    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
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
