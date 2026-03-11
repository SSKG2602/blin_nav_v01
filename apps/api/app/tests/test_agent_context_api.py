from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.llm.dependencies import get_llm_client
from app.main import app
from app.models import AgentLogORM, SessionContextORM, SessionORM
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.tools.dependencies import get_browser_runtime_client


class FakeBrowserRuntimeClient:
    def __init__(self) -> None:
        self.observation_payload: dict[str, Any] = {}
        self.screenshot_payload: dict[str, Any] = {
            "image_base64": "ZmFrZQ==",
            "mime_type": "image/png",
            "source": "runtime",
        }
        self.raise_observation_error = False

    def navigate_to_search_results(self, *, session_id, query, merchant) -> None:
        return

    def inspect_product_page(
        self,
        *,
        session_id,
        page_type,
        candidate_url: str | None = None,
        candidate_title: str | None = None,
    ) -> None:
        return

    def verify_product_variant(
        self,
        *,
        session_id,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        return

    def select_product_variant(
        self,
        *,
        session_id,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        return

    def add_to_cart(self, *, session_id) -> None:
        return

    def review_cart(self, *, session_id) -> None:
        return

    def perform_checkout(self, *, session_id) -> None:
        return

    def finalize_purchase(self, *, session_id) -> None:
        return

    def handle_error_recovery(self, *, session_id, error_type=None) -> None:
        return

    def get_current_page_observation(self, *, session_id) -> dict[str, Any]:
        if self.raise_observation_error:
            raise RuntimeError("observation unavailable")
        return dict(self.observation_payload)

    def get_current_page_screenshot(self, *, session_id) -> dict[str, Any]:
        return dict(self.screenshot_payload)


class FakeLLMClient:
    def __init__(self) -> None:
        self.raise_summary_error = False
        self.raise_multimodal_error = False
        self.summary_text = "I found a product and prepared a safe summary."
        self.multimodal_decision = MultimodalDecision.REQUIRE_USER_CONFIRMATION

    def score_product_candidates(self, *, query, candidates): return None

    def summarize_page_and_verification(self, page, verification) -> str:
        if self.raise_summary_error:
            raise RuntimeError("llm temporarily unavailable")
        return self.summary_text

    def analyze_multimodal_assessment(
        self,
        *,
        intent,
        page,
        verification,
        spoken_summary: str | None = None,
    ) -> MultimodalAssessment:
        if self.raise_multimodal_error:
            raise RuntimeError("multimodal analysis unavailable")
        decision = self.multimodal_decision
        return MultimodalAssessment(
            decision=decision,
            confidence=0.62,
            confidence_band=ConfidenceBand.MEDIUM,
            needs_user_confirmation=decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
            needs_sensitive_checkpoint=decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
            should_halt_low_confidence=decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
            ambiguity_notes=["Variant confirmation needed."],
            trust_notes=["Primary product evidence present."],
            review_notes=["Awaiting user confirmation."],
            reasoning_summary="Evidence is promising but requires explicit user confirmation.",
            recommended_next_step="ask_user_confirmation",
            notes="Fake multimodal assessment.",
        )


@pytest.fixture
def testing_session_local():
    assert SessionORM is not None
    assert AgentLogORM is not None
    assert SessionContextORM is not None

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
def fake_llm_client() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def client(testing_session_local, fake_browser_client: FakeBrowserRuntimeClient, fake_llm_client: FakeLLMClient):
    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_browser_runtime_client] = lambda: fake_browser_client
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_agent_step_updates_session_context_with_evidence(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    fake_llm_client: FakeLLMClient,
) -> None:
    fake_browser_client.observation_payload = {
        "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        "page_title": "HTC One M8 Android L 5.0 Lollipop",
        "detected_page_hints": ["product_detail"],
        "primary_product": {
            "title": "HTC One M8 Android L 5.0 Lollipop",
            "price_text": "$245.00",
            "summary_text": "Android smartphone",
            "quantity_text": "Qty: 1",
            "availability_text": "Add to cart available",
        },
    }
    fake_llm_client.summary_text = "This looks like a likely match. Please confirm before checkout."

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc phone",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert step_response.status_code == 200
    assert step_response.json()["new_state"] == "CART_VERIFICATION"

    context_response = client.get(f"/api/sessions/{session_id}/context")
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["latest_page_understanding"] is not None
    assert payload["latest_page_understanding"]["page_type"] == "PRODUCT_DETAIL"
    assert payload["latest_product_intent"] is not None
    assert payload["latest_verification"] is not None
    assert payload["latest_multimodal_assessment"] is not None
    assert (
        payload["latest_multimodal_assessment"]["decision"]
        == MultimodalDecision.REQUIRE_USER_CONFIRMATION.value
    )
    assert payload["latest_sensitive_checkpoint"] is None
    assert payload["latest_low_confidence_status"] is not None
    assert payload["latest_low_confidence_status"]["active"] is False
    assert payload["latest_recovery_status"] is not None
    assert payload["latest_recovery_status"]["active"] is False
    assert payload["latest_trust_assessment"] is not None
    assert payload["latest_review_assessment"] is not None
    assert payload["latest_final_purchase_confirmation"] is not None
    assert payload["latest_post_purchase_summary"] is not None
    assert payload["latest_spoken_summary"] == fake_llm_client.summary_text
    assert payload["latest_final_session_artifact"] is not None
    assert payload["latest_final_self_diagnosis"] is not None


def test_agent_step_persists_sensitive_checkpoint_when_required(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    fake_llm_client: FakeLLMClient,
) -> None:
    fake_llm_client.multimodal_decision = MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT
    fake_browser_client.observation_payload = {
        "observed_url": "https://demo.nopcommerce.com/login/checkoutasguest",
        "page_title": "Welcome, Please Sign In!",
        "detected_page_hints": ["checkout", "guest_checkout_entry_visible"],
        "checkout_ready": True,
        "primary_product": {"title": "HTC One M8 Android L 5.0 Lollipop", "price_text": "$245.00"},
    }

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]
    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc phone",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert step_response.status_code == 200

    context_response = client.get(f"/api/sessions/{session_id}/context")
    payload = context_response.json()
    assert payload["latest_multimodal_assessment"] is not None
    assert (
        payload["latest_multimodal_assessment"]["decision"]
        == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT.value
    )
    assert payload["latest_sensitive_checkpoint"] is not None
    assert payload["latest_sensitive_checkpoint"]["status"] == "PENDING"
    assert payload["latest_final_purchase_confirmation"] is not None
    assert payload["latest_final_purchase_confirmation"]["required"] is True


def test_get_session_context_missing_session_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/sessions/{uuid4()}/context")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_agent_step_persists_low_confidence_and_recovery_when_halt_required(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    fake_llm_client: FakeLLMClient,
) -> None:
    fake_llm_client.multimodal_decision = MultimodalDecision.HALT_LOW_CONFIDENCE
    fake_browser_client.observation_payload = {
        "observed_url": "https://demo.nopcommerce.com/unknown",
        "page_title": "Unknown",
        "detected_page_hints": ["unknown"],
    }

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]
    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc phone",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert step_response.status_code == 200

    context_response = client.get(f"/api/sessions/{session_id}/context")
    payload = context_response.json()
    assert payload["latest_low_confidence_status"] is not None
    assert payload["latest_low_confidence_status"]["active"] is True
    assert payload["latest_recovery_status"] is not None
    assert payload["latest_recovery_status"]["active"] is True


def test_agent_step_observation_failure_still_works(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    fake_browser_client.raise_observation_error = True

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc phone",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert step_response.status_code == 200

    context_response = client.get(f"/api/sessions/{session_id}/context")
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["latest_intent"] is not None
    assert payload["latest_page_understanding"] is not None
    assert payload["latest_page_understanding"]["page_type"] == "UNKNOWN"
    assert payload["latest_spoken_summary"] is not None


def test_agent_step_llm_failure_still_persists_safe_context(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    fake_llm_client: FakeLLMClient,
) -> None:
    fake_browser_client.observation_payload = {
        "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        "page_title": "HTC One M8 Android L 5.0 Lollipop",
        "detected_page_hints": ["product_detail"],
        "primary_product": {"title": "HTC One M8 Android L 5.0 Lollipop", "price_text": "$245.00"},
    }
    fake_llm_client.raise_summary_error = True
    fake_llm_client.raise_multimodal_error = True

    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc phone",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert step_response.status_code == 200

    context_response = client.get(f"/api/sessions/{session_id}/context")
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["latest_page_understanding"] is not None
    assert payload["latest_spoken_summary"] is not None
    assert payload["latest_spoken_summary"]
    assert payload["latest_multimodal_assessment"] is not None
    assert payload["latest_multimodal_assessment"]["decision"] in {
        MultimodalDecision.PROCEED.value,
        MultimodalDecision.HALT_LOW_CONFIDENCE.value,
        MultimodalDecision.REQUIRE_USER_CONFIRMATION.value,
    }
    assert payload["latest_multimodal_assessment"]["reasoning_summary"]
    assert (
        payload["latest_multimodal_assessment"]["notes"]
        == "Deterministic fallback multimodal assessment."
    )
    assert payload["latest_trust_assessment"] is not None
    assert payload["latest_review_assessment"] is not None


def test_runtime_observation_and_screenshot_proxy_routes(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
) -> None:
    fake_browser_client.observation_payload = {
        "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        "page_title": "Product detail",
        "detected_page_hints": ["product_detail"],
    }
    created = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"}).json()
    session_id = created["session_id"]

    observation = client.get(f"/api/sessions/{session_id}/runtime/observation")
    screenshot = client.get(f"/api/sessions/{session_id}/runtime/screenshot")

    assert observation.status_code == 200
    assert observation.json()["observed_url"] == fake_browser_client.observation_payload["observed_url"]
    assert screenshot.status_code == 200
    assert screenshot.json()["mime_type"] == "image/png"
    assert screenshot.json()["image_base64"] == fake_browser_client.screenshot_payload["image_base64"]
