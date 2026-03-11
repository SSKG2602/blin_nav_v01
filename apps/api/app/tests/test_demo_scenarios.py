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

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
        candidate_url: str | None = None,
        candidate_title: str | None = None,
    ) -> None:
        self._record(
            "inspect_product_page",
            session_id=session_id,
            page_type=page_type,
            candidate_url=candidate_url,
            candidate_title=candidate_title,
        )

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
        confidence = 0.22 if decision == MultimodalDecision.HALT_LOW_CONFIDENCE else 0.66
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
    response = client.post("/api/sessions", json={"merchant": "demo.nopcommerce.com"})
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


def _logs(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/sessions/{session_id}/logs")
    assert response.status_code == 200
    return response.json()


def _happy_path_observations() -> list[dict[str, Any]]:
    return [
        {
            "observed_url": "https://demo.nopcommerce.com",
            "page_title": "nopCommerce demo store",
            "detected_page_hints": ["home"],
        },
        {
            "observed_url": "https://demo.nopcommerce.com/search?q=htc",
            "page_title": "Search",
            "detected_page_hints": ["search_results"],
            "product_candidates": [
                {
                    "title": "HTC One M8 Android L 5.0 Lollipop",
                    "price_text": "$245.00",
                    "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                    "summary_text": "Android smartphone",
                }
            ],
        },
        {
            "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
            "page_title": "HTC One M8 Android L 5.0 Lollipop",
            "detected_page_hints": ["product_detail"],
            "primary_product": {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
                "summary_text": "Android smartphone",
                "quantity_text": "Qty: 1",
            },
        },
        {
            "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
            "page_title": "HTC One M8 Android L 5.0 Lollipop",
            "detected_page_hints": ["product_detail"],
            "primary_product": {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
                "summary_text": "Android smartphone",
                "quantity_text": "Qty: 1",
            },
        },
        {
            "observed_url": "https://demo.nopcommerce.com/cart",
            "page_title": "Shopping cart",
            "detected_page_hints": ["cart"],
            "cart_item_count": 1,
            "checkout_ready": True,
            "cart_items": [
                {
                    "item_id": "cart-item-1",
                    "title": "HTC One M8 Android L 5.0 Lollipop",
                    "price_text": "$245.00",
                    "quantity_text": "1",
                }
            ],
            "primary_product": {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
            },
        },
        {
            "observed_url": "https://demo.nopcommerce.com/login/checkoutasguest",
            "page_title": "Welcome, Please Sign In!",
            "detected_page_hints": ["checkout", "guest_checkout_entry_visible"],
            "checkout_ready": True,
            "primary_product": {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
            },
            "notes": "guest_checkout_entry_visible",
        },
        {
            "observed_url": "https://demo.nopcommerce.com/login/checkoutasguest",
            "page_title": "Welcome, Please Sign In!",
            "detected_page_hints": ["checkout", "guest_checkout_entry_visible"],
            "checkout_ready": True,
            "primary_product": {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
            },
            "notes": "guest_checkout_entry_visible",
        },
    ]


def _required_options_blocker_observations() -> list[dict[str, Any]]:
    return [
        {
            "observed_url": "https://demo.nopcommerce.com",
            "page_title": "nopCommerce demo store",
            "detected_page_hints": ["home"],
        },
        {
            "observed_url": "https://demo.nopcommerce.com/search?q=build+your+own+computer",
            "page_title": "Search",
            "detected_page_hints": ["search_results"],
            "product_candidates": [
                {
                    "title": "Build your own computer",
                    "price_text": "$1,200.00",
                    "url": "https://demo.nopcommerce.com/build-your-own-computer",
                    "summary_text": "Desktop computer demo fixture",
                }
            ],
        },
        {
            "observed_url": "https://demo.nopcommerce.com/build-your-own-computer",
            "page_title": "Build your own computer",
            "detected_page_hints": ["product_detail", "option_selection_required"],
            "primary_product": {
                "title": "Build your own computer",
                "price_text": "$1,200.00",
                "summary_text": "Desktop computer demo fixture",
                "variant_options": ["Processor *", "RAM *", "HDD *"],
            },
            "notes": "option_selection_required, required_options:Processor *; RAM *; HDD *",
        },
        {
            "observed_url": "https://demo.nopcommerce.com/build-your-own-computer",
            "page_title": "Build your own computer",
            "detected_page_hints": ["product_detail", "option_selection_required"],
            "primary_product": {
                "title": "Build your own computer",
                "price_text": "$1,200.00",
                "summary_text": "Desktop computer demo fixture",
                "variant_options": ["Processor *", "RAM *", "HDD *"],
            },
            "notes": "option_selection_required, required_options:Processor *; RAM *; HDD *",
        },
    ]


def _modal_recovery_observations() -> list[dict[str, Any]]:
    return [
        {
            "observed_url": "https://demo.nopcommerce.com/build-your-own-computer",
            "page_title": "Build your own computer",
            "detected_page_hints": ["product_detail", "option_selection_required"],
            "notes": "modal interruption detected while parsing page",
            "primary_product": {"title": "Build your own computer", "price_text": "$1,200.00"},
        },
        {
            "observed_url": "https://demo.nopcommerce.com/build-your-own-computer",
            "page_title": "Build your own computer",
            "detected_page_hints": ["product_detail", "option_selection_required"],
            "notes": "modal interruption detected while parsing page",
            "primary_product": {"title": "Build your own computer", "price_text": "$1,200.00"},
        },
    ]


def test_demo_happy_path_stops_at_guest_checkout_entry(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.PROCEED])
    browser.queue_observations(_happy_path_observations())

    session_id = _create_session(client)
    step = _run_user_step(
        client,
        session_id,
            {
                "event_type": "user_intent_parsed",
                "intent": "search_products",
                "query": "one m8",
                "merchant": "demo.nopcommerce.com",
            },
        )
    assert step["new_state"] == "FINAL_CONFIRMATION"
    assert step["commands"]
    assert (
        step["spoken_summary"]
        == "Checkout entry reached for HTC One M8 Android L 5.0 Lollipop. Stopping before guest checkout."
    )

    context = _context(client, session_id)
    assert context["latest_page_understanding"] is not None
    assert context["latest_page_understanding"]["page_type"] == "CHECKOUT"
    assert context["latest_verification"] is not None
    assert context["latest_spoken_summary"] is not None
    assert context["latest_multimodal_assessment"]["decision"] == "PROCEED"
    assert context["latest_low_confidence_status"]["active"] is False
    assert context["latest_recovery_status"]["active"] is False
    assert context["latest_sensitive_checkpoint"] is None
    assert context["latest_final_purchase_confirmation"]["required"] is True
    assert "boundary" in (context["latest_final_purchase_confirmation"]["notes"] or "").lower()
    assert context["latest_cart_snapshot"]["cart_item_count"] == 1
    assert not any(call["method"] == "finalize_purchase" for call in browser.calls)


def test_demo_golden_happy_path_audit_and_micro_summaries_are_replayable(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.PROCEED])
    browser.queue_observations(_happy_path_observations())

    session_id = _create_session(client)
    _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "one m8",
            "merchant": "demo.nopcommerce.com",
        },
    )

    audit_logs = [entry for entry in _logs(client, session_id) if entry.get("tool_name") == "agent.audit"]
    spoken_summaries = [entry.get("user_spoken_summary") for entry in audit_logs]

    assert any(summary == "Results loaded. I found 1 candidate on the demo store." for summary in spoken_summaries)
    assert any(summary == "Product verified: HTC One M8 Android L 5.0 Lollipop at $245.00." for summary in spoken_summaries)
    assert any(summary == "Added to cart: HTC One M8 Android L 5.0 Lollipop. Cart verified with 1 item." for summary in spoken_summaries)
    assert any(
        summary == "Checkout entry reached for HTC One M8 Android L 5.0 Lollipop. Stopping before guest checkout."
        for summary in spoken_summaries
    )
    assert any("page=SEARCH_RESULTS" in (entry.get("tool_input_excerpt") or "") for entry in audit_logs)
    assert any("verification=MATCH" in (entry.get("tool_output_excerpt") or "") for entry in audit_logs)
    assert any("cart=1" in (entry.get("tool_output_excerpt") or "") for entry in audit_logs)
    assert any("checkout_stop=guest_checkout_entry_visible" in (entry.get("tool_output_excerpt") or "") for entry in audit_logs)


def test_demo_blocker_path_requests_clarification_before_add_to_cart(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.PROCEED])
    browser.queue_observations(_required_options_blocker_observations())

    session_id = _create_session(client)
    step = _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "build your own computer",
            "merchant": "demo.nopcommerce.com",
        },
    )

    assert step["new_state"] == "CLARIFICATION_REQUIRED"
    assert (
        step["spoken_summary"]
        == "Product blocked before add to cart. Build your own computer still needs required options selected."
    )
    action_methods = [
        call["method"]
        for call in browser.calls
        if call["method"] not in {"get_current_page_observation", "get_current_page_screenshot"}
    ]
    assert action_methods == [
        "navigate_to_search_results",
        "inspect_product_page",
        "select_product_variant",
    ]

    context = _context(client, session_id)
    clarification = context["latest_clarification_request"]
    assert clarification["kind"] == "VARIANT_PRECISION"
    assert "required options" in clarification["prompt_to_user"].lower()
    assert context["latest_page_understanding"]["page_type"] == "PRODUCT_DETAIL"
    assert "option_selection_required" in context["latest_page_understanding"]["detected_page_hints"]

    audit_logs = [entry for entry in _logs(client, session_id) if entry.get("tool_name") == "agent.audit"]
    assert any("blocker=required_options" in (entry.get("tool_output_excerpt") or "") for entry in audit_logs)



def test_demo_ambiguous_product_scenario_requests_clarification(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.REQUIRE_USER_CONFIRMATION])
    browser.queue_observations(
        [
            {
                "observed_url": "https://demo.nopcommerce.com/search?q=htc+one",
                "page_title": "Search",
                "detected_page_hints": ["search_results"],
                "product_candidates": [
                    {
                        "title": "HTC One Mini Blue",
                        "price_text": "$189.00",
                        "url": "https://demo.nopcommerce.com/htc-one-mini-blue",
                    },
                    {
                        "title": "HTC One M8 Android L 5.0 Lollipop",
                        "price_text": "$245.00",
                        "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                    },
                ],
            },
            {
                "observed_url": "https://demo.nopcommerce.com/search?q=htc+one",
                "page_title": "Search",
                "detected_page_hints": ["search_results"],
                "product_candidates": [
                    {
                        "title": "HTC One Mini Blue",
                        "price_text": "$189.00",
                        "url": "https://demo.nopcommerce.com/htc-one-mini-blue",
                    },
                    {
                        "title": "HTC One M8 Android L 5.0 Lollipop",
                        "price_text": "$245.00",
                        "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                    },
                ],
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
            "query": "htc one",
            "merchant": "demo.nopcommerce.com",
        },
    )

    assert step["new_state"] == "CLARIFICATION_REQUIRED"
    context = _context(client, session_id)
    clarification = context["latest_clarification_request"]
    assert clarification["kind"] == "PRODUCT_SELECTION"
    assert len(clarification["candidate_options"]) == 2


def test_demo_sensitive_checkpoint_scenario_with_resolution(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT])

    browser.queue_observations(_happy_path_observations())
    approved_session = _create_session(client)
    _run_user_step(
        client,
        approved_session,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "one m8",
            "merchant": "demo.nopcommerce.com",
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

    browser.queue_observations(_happy_path_observations())
    rejected_session = _create_session(client)
    _run_user_step(
        client,
        rejected_session,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "one m8",
            "merchant": "demo.nopcommerce.com",
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
            },
            {
                "observed_url": "https://example.invalid/weak-signals",
                "page_title": "Unknown page",
            },
        ]
    )
    session_id = _create_session(client)
    _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc phone",
            "merchant": "demo.nopcommerce.com",
        },
    )
    context = _context(client, session_id)
    assert context["latest_multimodal_assessment"]["decision"] == "HALT_LOW_CONFIDENCE"
    assert context["latest_low_confidence_status"]["active"] is True


def test_demo_recovery_path_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.REQUIRE_USER_CONFIRMATION])
    browser.queue_observations(_modal_recovery_observations())
    session_id = _create_session(client)
    step = _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "computer",
            "merchant": "demo.nopcommerce.com",
        },
    )
    assert step["new_state"] == "ERROR_RECOVERY"
    assert step["spoken_summary"] == "Recovery engaged on product_detail. Page indicates modal interruption signals."

    context = _context(client, session_id)
    assert context["latest_recovery_status"]["active"] is True
    assert context["latest_recovery_status"]["recovery_kind"] in {
        "MODAL_INTERRUPTION",
        "PAGE_DESYNC",
        "NAVIGATION_RECOVERY",
    }
    assert not any(call["method"] in {"add_to_cart", "perform_checkout"} for call in browser.calls)

    audit_logs = [entry for entry in _logs(client, session_id) if entry.get("tool_name") == "agent.audit"]
    assert any("recovery=MODAL_INTERRUPTION" in (entry.get("tool_output_excerpt") or "") for entry in audit_logs)


def test_demo_layout_shift_recovery_scenario(scenario_env) -> None:
    client, browser, llm = scenario_env
    llm.queue_decisions([MultimodalDecision.HALT_LOW_CONFIDENCE])
    browser.queue_observations(
        [
            {
                "observed_url": "https://demo.nopcommerce.com/search?q=htc",
                "page_title": "Search",
                "detected_page_hints": ["unknown"],
                "notes": "layout shift detected while trying to stabilize search results",
            },
            {
                "observed_url": "https://demo.nopcommerce.com/search?q=htc",
                "page_title": "Search",
                "detected_page_hints": ["unknown"],
                "notes": "layout shift detected while trying to stabilize search results",
            },
        ]
    )

    session_id = _create_session(client)
    _run_user_step(
        client,
        session_id,
        {
            "event_type": "user_intent_parsed",
            "intent": "search_products",
            "query": "htc",
            "merchant": "demo.nopcommerce.com",
        },
    )

    context = _context(client, session_id)
    assert context["latest_low_confidence_status"]["active"] is True
    assert context["latest_recovery_status"]["active"] is True
