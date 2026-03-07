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
        self.raise_observation_error = False

    def navigate_to_search_results(self, *, session_id, query, merchant) -> None:
        return

    def inspect_product_page(self, *, session_id, page_type) -> None:
        return

    def verify_product_variant(self, *, session_id) -> None:
        return

    def review_cart(self, *, session_id) -> None:
        return

    def perform_checkout(self, *, session_id) -> None:
        return

    def handle_error_recovery(self, *, session_id, error_type=None) -> None:
        return

    def get_current_page_observation(self, *, session_id) -> dict[str, Any]:
        if self.raise_observation_error:
            raise RuntimeError("observation unavailable")
        return dict(self.observation_payload)


class FakeLLMClient:
    def __init__(self) -> None:
        self.raise_summary_error = False
        self.raise_multimodal_error = False
        self.summary_text = "I found a product and prepared a safe summary."
        self.multimodal_decision = MultimodalDecision.REQUIRE_USER_CONFIRMATION

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
        "observed_url": "https://www.amazon.in/dp/B0TESTSKU",
        "page_title": "Pedigree Adult Dog Food 3kg",
        "detected_page_hints": ["product_detail"],
        "primary_product": {
            "title": "Pedigree Adult Dog Food 3kg",
            "price_text": "₹799",
            "availability_text": "In stock",
        },
    }
    fake_llm_client.summary_text = "This looks like a likely match. Please confirm before checkout."

    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food 3kg",
            "merchant": "amazon.in",
        },
    )
    assert step_response.status_code == 200
    assert step_response.json()["new_state"] == "SEARCHING_PRODUCTS"

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


def test_agent_step_persists_sensitive_checkpoint_when_required(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    fake_llm_client: FakeLLMClient,
) -> None:
    fake_llm_client.multimodal_decision = MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT
    fake_browser_client.observation_payload = {
        "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
        "page_title": "Checkout",
        "detected_page_hints": ["checkout"],
        "checkout_ready": True,
        "primary_product": {"title": "Pedigree Adult Dog Food 3kg", "price_text": "₹799"},
    }

    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food 3kg",
            "merchant": "amazon.in",
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
        "observed_url": "https://www.amazon.in/unknown",
        "page_title": "Unknown",
        "detected_page_hints": ["unknown"],
    }

    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]
    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food",
            "merchant": "amazon.in",
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

    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food",
            "merchant": "amazon.in",
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
        "observed_url": "https://www.amazon.in/dp/B0TESTSKU",
        "page_title": "Pedigree Adult Dog Food 3kg",
        "detected_page_hints": ["product_detail"],
        "primary_product": {"title": "Pedigree Adult Dog Food 3kg", "price_text": "₹799"},
    }
    fake_llm_client.raise_summary_error = True
    fake_llm_client.raise_multimodal_error = True

    created = client.post("/api/sessions", json={"merchant": "amazon.in"}).json()
    session_id = created["session_id"]

    step_response = client.post(
        f"/api/sessions/{session_id}/agent/step",
        json={
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food",
            "merchant": "amazon.in",
        },
    )
    assert step_response.status_code == 200

    context_response = client.get(f"/api/sessions/{session_id}/context")
    assert context_response.status_code == 200
    payload = context_response.json()
    assert payload["latest_page_understanding"] is not None
    assert payload["latest_spoken_summary"] is not None
    assert "searching products" in payload["latest_spoken_summary"].lower()
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
