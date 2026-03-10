from __future__ import annotations

from typing import Any
from uuid import UUID

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


class ScenarioBrowserRuntimeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._observations: list[dict[str, Any]] = []

    def queue_observations(self, observations: list[dict[str, Any]]) -> None:
        self._observations = [dict(item) for item in observations]

    def _record(self, method: str, **payload: Any) -> None:
        self.calls.append({"method": method, **payload})

    def _next_observation(self) -> dict[str, Any]:
        if self._observations:
            return self._observations.pop(0)
        return {}

    def navigate_to_search_results(self, *, session_id: UUID, query: str | None, merchant) -> None:
        self._record("navigate_to_search_results", session_id=session_id, query=query, merchant=merchant)

    def inspect_product_page(self, *, session_id: UUID, page_type: str | None) -> None:
        self._record("inspect_product_page", session_id=session_id, page_type=page_type)

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self._record("verify_product_variant", session_id=session_id)

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self._record(
            "select_product_variant",
            session_id=session_id,
            variant_hint=variant_hint,
            size_hint=size_hint,
            color_hint=color_hint,
        )

    def add_to_cart(self, *, session_id: UUID) -> None:
        self._record("add_to_cart", session_id=session_id)

    def review_cart(self, *, session_id: UUID) -> None:
        self._record("review_cart", session_id=session_id)

    def perform_checkout(self, *, session_id: UUID) -> None:
        self._record("perform_checkout", session_id=session_id)

    def finalize_purchase(self, *, session_id: UUID) -> None:
        self._record("finalize_purchase", session_id=session_id)

    def handle_error_recovery(self, *, session_id: UUID, error_type: str | None = None) -> None:
        self._record("handle_error_recovery", session_id=session_id, error_type=error_type)

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        self._record("get_current_page_observation", session_id=session_id)
        return self._next_observation()

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        self._record("get_current_page_screenshot", session_id=session_id)
        return {}


class ScenarioLLMClient:
    def __init__(self) -> None:
        self.summary_text = "Deterministic scenario summary."
        self._decisions: list[MultimodalDecision] = [MultimodalDecision.PROCEED]

    def score_product_candidates(self, *, query, candidates): return None

    def queue_decisions(self, decisions: list[MultimodalDecision]) -> None:
        self._decisions = list(decisions) if decisions else [MultimodalDecision.PROCEED]

    def _next_decision(self) -> MultimodalDecision:
        if len(self._decisions) > 1:
            return self._decisions.pop(0)
        return self._decisions[0]

    def summarize_page_and_verification(self, page, verification) -> str:
        return self.summary_text

    def analyze_multimodal_assessment(
        self,
        *,
        intent,
        page,
        verification,
        spoken_summary: str | None = None,
    ) -> MultimodalAssessment:
        decision = self._next_decision()
        return MultimodalAssessment(
            decision=decision,
            confidence=0.66,
            confidence_band=ConfidenceBand.MEDIUM,
            needs_user_confirmation=decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
            needs_sensitive_checkpoint=decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
            should_halt_low_confidence=decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
            ambiguity_notes=["deterministic ambiguity note"],
            trust_notes=["deterministic trust note"],
            review_notes=["deterministic review note"],
            reasoning_summary=f"Deterministic decision: {decision.value}.",
            recommended_next_step="scenario_next_step",
            notes="Scenario fake multimodal assessment.",
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
def scenario_env(testing_session_local):
    browser_client = ScenarioBrowserRuntimeClient()
    llm_client = ScenarioLLMClient()

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_browser_runtime_client] = lambda: browser_client
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    with TestClient(app) as test_client:
        yield test_client, browser_client, llm_client
    app.dependency_overrides.clear()


def _create_session(client: TestClient) -> str:
    response = client.post("/api/sessions", json={"merchant": "amazon.in"})
    assert response.status_code == 201
    return response.json()["session_id"]


def _run_user_step(client: TestClient, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/api/sessions/{session_id}/agent/step", json=payload)
    assert response.status_code == 200
    return response.json()


def _context(client: TestClient, session_id: str) -> dict[str, Any]:
    response = client.get(f"/api/sessions/{session_id}/context")
    assert response.status_code == 200
    return response.json()


def test_demo_happy_path_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.PROCEED])
    browser.queue_observations(
        [
            {
                "observed_url": "https://www.amazon.in",
                "page_title": "Amazon.in",
                "detected_page_hints": ["home"],
            },
            {
                "observed_url": "https://www.amazon.in/s?k=pedigree+dog+food+3kg",
                "page_title": "Results",
                "detected_page_hints": ["search_results"],
                "product_candidates": [
                    {
                        "title": "Pedigree dog food 3kg",
                        "price_text": "₹799",
                        "url": "https://www.amazon.in/dp/B0HAPPYCASE",
                        "rating_text": "4.4 out of 5 stars",
                        "review_count_text": "12,345 ratings",
                        "variant_text": "3kg",
                    }
                ],
            },
            {
                "observed_url": "https://www.amazon.in/dp/B0HAPPYCASE",
                "page_title": "Pedigree dog food 3kg",
                "detected_page_hints": ["product_detail"],
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                    "rating_text": "4.4 out of 5 stars",
                    "review_count_text": "12,345 ratings",
                    "variant_text": "3kg",
                },
            },
            {
                "observed_url": "https://www.amazon.in/dp/B0HAPPYCASE",
                "page_title": "Pedigree dog food 3kg",
                "detected_page_hints": ["product_detail"],
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                    "rating_text": "4.4 out of 5 stars",
                    "review_count_text": "12,345 ratings",
                    "variant_text": "3kg",
                },
            },
            {
                "observed_url": "https://www.amazon.in/gp/cart/view.html",
                "page_title": "Shopping Cart",
                "detected_page_hints": ["cart"],
                "cart_item_count": 1,
                "checkout_ready": True,
                "cart_items": [
                    {
                        "item_id": "cart-item-1",
                        "title": "Pedigree dog food 3kg",
                        "price_text": "₹799",
                        "quantity_text": "1",
                    }
                ],
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
                "page_title": "Checkout",
                "detected_page_hints": ["checkout"],
                "checkout_ready": True,
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
                "page_title": "Checkout",
                "detected_page_hints": ["checkout"],
                "checkout_ready": True,
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
        ]
    )

    session_id = _create_session(client)
    step = _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "pedigree dog food 3kg",
            "merchant": "amazon.in",
        },
    )
    assert step["new_state"] == "FINAL_CONFIRMATION"
    assert step["commands"]

    context = _context(client, session_id)
    assert context["latest_page_understanding"] is not None
    assert context["latest_verification"] is not None
    assert context["latest_spoken_summary"] is not None
    assert context["latest_multimodal_assessment"]["decision"] == "PROCEED"
    assert context["latest_low_confidence_status"]["active"] is False
    assert context["latest_recovery_status"]["active"] is False
    assert context["latest_sensitive_checkpoint"] is None
    assert context["latest_final_purchase_confirmation"]["required"] is True
    assert context["latest_cart_snapshot"]["cart_item_count"] == 1


def test_demo_ambiguous_product_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.REQUIRE_USER_CONFIRMATION])
    browser.queue_observations(
        [
            {
                "observed_url": "https://www.amazon.in/dp/B0AMBIGUOUS",
                "page_title": "Dog treats combo",
                "detected_page_hints": ["product_detail"],
                "primary_product": {
                    "title": "Dog treats combo",
                    "price_text": "₹499",
                    "rating_text": "4.0 out of 5 stars",
                    "review_count_text": "23 ratings",
                },
            }
        ]
    )

    session_id = _create_session(client)
    _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "dog food",
            "merchant": "amazon.in",
        },
    )
    context = _context(client, session_id)

    assert context["latest_verification"] is not None
    assert context["latest_verification"]["decision"] in {"PARTIAL_MATCH", "AMBIGUOUS"}
    assert context["latest_multimodal_assessment"]["decision"] == "REQUIRE_USER_CONFIRMATION"
    assert context["latest_multimodal_assessment"]["needs_user_confirmation"] is True
    assert context["latest_multimodal_assessment"]["ambiguity_notes"]


def test_demo_sensitive_checkpoint_scenario_with_resolution(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions(
        [
            MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
            MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
        ]
    )
    browser.queue_observations(
        [
            {
                "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
                "page_title": "Checkout payment confirmation",
                "detected_page_hints": ["checkout"],
                "checkout_ready": True,
                "primary_product": {"title": "Pedigree dog food 3kg", "price_text": "₹799"},
            },
            {
                "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
                "page_title": "Checkout payment confirmation",
                "detected_page_hints": ["checkout"],
                "checkout_ready": True,
                "primary_product": {"title": "Pedigree dog food 3kg", "price_text": "₹799"},
            },
        ]
    )

    approved_session = _create_session(client)
    _run_user_step(
        client,
        approved_session,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "pedigree dog food 3kg",
            "merchant": "amazon.in",
        },
    )

    checkpoint = client.get(f"/api/sessions/{approved_session}/checkpoint")
    assert checkpoint.status_code == 200
    assert checkpoint.json()["status"] == "PENDING"

    resolve_ok = client.post(
        f"/api/sessions/{approved_session}/checkpoint/resolve",
        json={"approved": True, "resolution_notes": "approved in scenario"},
    )
    assert resolve_ok.status_code == 200
    assert resolve_ok.json()["status"] == "APPROVED"
    approved_context = _context(client, approved_session)
    assert approved_context["latest_final_purchase_confirmation"]["required"] is True
    assert approved_context["latest_final_purchase_confirmation"]["confirmed"] is False

    rejected_session = _create_session(client)
    _run_user_step(
        client,
        rejected_session,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "pedigree dog food 3kg",
            "merchant": "amazon.in",
        },
    )
    resolve_no = client.post(
        f"/api/sessions/{rejected_session}/checkpoint/resolve",
        json={"approved": False, "resolution_notes": "rejected in scenario"},
    )
    assert resolve_no.status_code == 200
    assert resolve_no.json()["status"] == "REJECTED"
    rejected_context = _context(client, rejected_session)
    assert rejected_context["latest_final_purchase_confirmation"]["required"] is True
    assert rejected_context["latest_final_purchase_confirmation"]["confirmed"] is False


def test_demo_low_confidence_halt_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.HALT_LOW_CONFIDENCE])
    browser.queue_observations(
        [
            {
                "observed_url": "https://example.invalid/weak-signals",
                "page_title": "Unknown page",
            }
        ]
    )
    session_id = _create_session(client)
    _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food",
            "merchant": "amazon.in",
        },
    )
    context = _context(client, session_id)
    assert context["latest_multimodal_assessment"]["decision"] == "HALT_LOW_CONFIDENCE"
    assert context["latest_low_confidence_status"]["active"] is True


def test_demo_recovery_path_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.REQUIRE_USER_CONFIRMATION])
    browser.queue_observations(
        [
            {
                "observed_url": "https://www.amazon.in/dp/B0RECOVERY",
                "page_title": "Product page",
                "detected_page_hints": ["product_detail"],
                "notes": "modal interruption detected while parsing page",
                "primary_product": {"title": "Pedigree dog food 3kg", "price_text": "₹799"},
            }
        ]
    )
    session_id = _create_session(client)
    step = _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "dog food",
            "merchant": "amazon.in",
        },
    )
    assert step["new_state"] in {"SEARCHING_PRODUCTS", "ERROR_RECOVERY"}

    context = _context(client, session_id)
    assert context["latest_recovery_status"]["active"] is True
    assert context["latest_recovery_status"]["recovery_kind"] in {
        "MODAL_INTERRUPTION",
        "PAGE_DESYNC",
        "NAVIGATION_RECOVERY",
    }


def test_demo_post_purchase_summary_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.PROCEED])
    browser.queue_observations(
        [
            {
                "observed_url": "https://www.amazon.in",
                "page_title": "Amazon.in",
                "detected_page_hints": ["home"],
            },
            {
                "observed_url": "https://www.amazon.in/s?k=pedigree+dog+food+3kg",
                "page_title": "Results",
                "detected_page_hints": ["search_results"],
                "product_candidates": [
                    {
                        "title": "Pedigree dog food 3kg",
                        "price_text": "₹799",
                        "url": "https://www.amazon.in/dp/B0POSTPURCHASE",
                        "variant_text": "3kg",
                    }
                ],
            },
            {
                "observed_url": "https://www.amazon.in/dp/B0POSTPURCHASE",
                "page_title": "Pedigree dog food 3kg",
                "detected_page_hints": ["product_detail"],
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/dp/B0POSTPURCHASE",
                "page_title": "Pedigree dog food 3kg",
                "detected_page_hints": ["product_detail"],
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/gp/cart/view.html",
                "page_title": "Shopping Cart",
                "detected_page_hints": ["cart"],
                "cart_item_count": 1,
                "checkout_ready": True,
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
                "page_title": "Checkout",
                "detected_page_hints": ["checkout"],
                "checkout_ready": True,
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
                "page_title": "Checkout",
                "detected_page_hints": ["checkout"],
                "checkout_ready": True,
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
            },
            {
                "observed_url": "https://www.amazon.in/order-confirmation",
                "page_title": "Thank you, your order has been placed",
                "detected_page_hints": ["checkout"],
                "delivery_window_text": "Delivery by Monday",
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
                "notes": "order_confirmation_detected",
            },
            {
                "observed_url": "https://www.amazon.in/order-confirmation",
                "page_title": "Thank you, your order has been placed",
                "detected_page_hints": ["checkout"],
                "delivery_window_text": "Delivery by Monday",
                "primary_product": {
                    "title": "Pedigree dog food 3kg",
                    "price_text": "₹799",
                },
                "notes": "order_confirmation_detected",
            }
        ]
    )
    session_id = _create_session(client)
    step = _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "pedigree dog food 3kg",
            "merchant": "amazon.in",
        },
    )
    assert step["new_state"] == "FINAL_CONFIRMATION"
    resolve = client.post(
        f"/api/sessions/{session_id}/final-confirmation/resolve",
        json={"approved": True, "resolution_notes": "approved in post-purchase scenario"},
    )
    assert resolve.status_code == 200
    context = _context(client, session_id)
    assert context["latest_post_purchase_summary"] is not None
    assert "order appears placed" in context["latest_post_purchase_summary"]["spoken_summary"].lower()
    assert context["latest_post_purchase_summary"]["order_item_title"] == "Pedigree dog food 3kg"
