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
from app.live.dependencies import get_live_speech_provider
from app.main import app
from app.models import AgentLogORM, SessionContextORM, SessionORM
from app.repositories.session_context_repo import update_session_context
from app.repositories.session_repo import append_agent_log
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.control_state import CheckpointStatus, SensitiveCheckpointKind, SensitiveCheckpointRequest
from app.schemas.intent import InterpretedUserIntent, ShoppingAction
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.product_verification import ProductIntentSpec
from app.schemas.purchase_support import FinalPurchaseConfirmation
from app.tools.dependencies import get_browser_runtime_client
from app.llm.dependencies import get_llm_client


class FakeBrowserRuntimeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.observation_payload: dict[str, Any] = {
            "observed_url": "https://www.amazon.in/s?k=dog+food",
            "page_title": "Results",
            "detected_page_hints": ["search_results"],
            "product_candidates": [{"title": "Pedigree Dog Food", "price_text": "₹799"}],
        }

    def navigate_to_search_results(self, *, session_id: UUID, query: str | None, merchant) -> None:
        self.calls.append({"method": "navigate_to_search_results", "session_id": session_id, "query": query})
        return

    def inspect_product_page(self, *, session_id: UUID, page_type: str | None) -> None:
        self.calls.append({"method": "inspect_product_page", "session_id": session_id, "page_type": page_type})
        return

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self.calls.append({"method": "verify_product_variant", "session_id": session_id})
        return

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self.calls.append({"method": "select_product_variant", "session_id": session_id})
        return

    def add_to_cart(self, *, session_id: UUID) -> None:
        self.calls.append({"method": "add_to_cart", "session_id": session_id})
        return

    def review_cart(self, *, session_id: UUID) -> None:
        self.calls.append({"method": "review_cart", "session_id": session_id})
        return

    def perform_checkout(self, *, session_id: UUID) -> None:
        self.calls.append({"method": "perform_checkout", "session_id": session_id})
        return

    def finalize_purchase(self, *, session_id: UUID) -> None:
        self.calls.append({"method": "finalize_purchase", "session_id": session_id})
        self.observation_payload = {
            "observed_url": "https://www.amazon.in/gp/your-account/order-confirmation",
            "page_title": "Thank you, your order has been placed",
            "detected_page_hints": ["checkout"],
            "primary_product": {"title": "Pedigree Dog Food", "price_text": "₹799"},
            "notes": "order_confirmation_detected",
        }
        return

    def handle_error_recovery(self, *, session_id: UUID, error_type: str | None = None) -> None:
        self.calls.append({"method": "handle_error_recovery", "session_id": session_id, "error_type": error_type})
        return

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        return dict(self.observation_payload)

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        return {}


class FakeLLMClient:
    def __init__(self) -> None:
        self.multimodal_decision = MultimodalDecision.PROCEED

    def interpret_user_intent(self, utterance: str) -> InterpretedUserIntent:
        return InterpretedUserIntent(
            raw_utterance=utterance,
            action=ShoppingAction.SEARCH_PRODUCT,
            merchant="amazon.in",
            product_intent=ProductIntentSpec(raw_query=utterance, product_name=utterance),
            confidence=0.8,
            requires_clarification=False,
            spoken_confirmation="Understood.",
            notes="live test intent",
        )

    def summarize_page_and_verification(self, page, verification) -> str:
        return "Live summary."

    def analyze_multimodal_assessment(
        self,
        *,
        intent,
        page,
        verification,
        spoken_summary: str | None = None,
    ) -> MultimodalAssessment:
        decision = self.multimodal_decision
        return MultimodalAssessment(
            decision=decision,
            confidence=0.7,
            confidence_band=ConfidenceBand.MEDIUM,
            needs_user_confirmation=decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
            needs_sensitive_checkpoint=decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
            should_halt_low_confidence=decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
            ambiguity_notes=[],
            trust_notes=[],
            review_notes=[],
            reasoning_summary="live test multimodal",
            recommended_next_step="continue",
            notes="live test",
        )

    def analyze_visual_page(
        self,
        *,
        raw_observation: dict[str, object],
        screenshot: dict[str, object] | None,
    ) -> dict[str, object]:
        return {}


class FakeSpeechProvider:
    def __init__(self) -> None:
        self.raise_on_synthesize = False

    def transcribe_audio_chunk(
        self,
        *,
        audio_base64: str,
        locale: str | None = None,
        transcript_hint: str | None = None,
    ) -> str | None:
        return transcript_hint or "search dog food"

    def synthesize_text(
        self,
        *,
        text: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        if self.raise_on_synthesize:
            raise RuntimeError("tts unavailable")
        return {
            "text": text,
            "audio_base64": None,
            "provider": "fake",
            "locale": locale,
            "playback_mode": "browser_tts",
        }


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
def fake_speech_provider() -> FakeSpeechProvider:
    return FakeSpeechProvider()


@pytest.fixture
def client(
    testing_session_local,
    fake_browser_client: FakeBrowserRuntimeClient,
    fake_llm_client: FakeLLMClient,
    fake_speech_provider: FakeSpeechProvider,
):
    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_browser_runtime_client] = lambda: fake_browser_client
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    app.dependency_overrides[get_live_speech_provider] = lambda: fake_speech_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_live_session(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/live/sessions", json={"merchant": "amazon.in"})
    assert response.status_code == 201
    return response.json()


def _seed_live_control_state(
    testing_session_local,
    *,
    session_id: str,
    state_after: str,
    checkpoint: SensitiveCheckpointRequest | None = None,
    final_confirmation: FinalPurchaseConfirmation | None = None,
) -> None:
    with testing_session_local() as db:
        append_agent_log(
            db,
            AgentLogEntry(
                session_id=UUID(session_id),
                step_type=AgentStepType.META,
                state_before=None,
                state_after=state_after,
                tool_name="test.seed",
                tool_output_excerpt=f"seeded {state_after}",
            ),
        )
        update_session_context(
            db,
            UUID(session_id),
            latest_sensitive_checkpoint=checkpoint,
            latest_final_purchase_confirmation=final_confirmation,
        )


def test_create_live_session_endpoint(client: TestClient) -> None:
    payload = _create_live_session(client)
    assert "session_id" in payload
    assert payload["websocket_path"].startswith("/api/live/sessions/")
    assert payload["locale"] == "en-IN"


def test_create_live_session_endpoint_normalizes_locale(client: TestClient) -> None:
    response = client.post("/api/live/sessions", json={"merchant": "amazon.in", "locale": "hi-IN"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["locale"] == "hi-IN"


def test_live_websocket_user_text_flow(client: TestClient) -> None:
    payload = _create_live_session(client)
    websocket_path = payload["websocket_path"]

    with client.websocket_connect(websocket_path) as websocket:
        connected = websocket.receive_json()
        assert connected["event"] == "session_connected"
        assert connected["data"]["locale"] == "en-IN"

        websocket.send_json({"type": "start"})
        started = websocket.receive_json()
        assert started["event"] == "session_started"
        assert started["data"]["locale"] == "en-IN"

        websocket.send_json({"type": "user_text", "text": "find dog food"})
        events = [websocket.receive_json() for _ in range(3)]
        names = {event["event"] for event in events}
        assert "interpreted_intent" in names
        assert "agent_step" in names
        assert "spoken_output" in names


def test_live_websocket_checkpoint_event_emitted(
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
        "primary_product": {"title": "Pedigree Dog Food", "price_text": "₹799"},
    }
    payload = _create_live_session(client)
    websocket_path = payload["websocket_path"]

    with client.websocket_connect(websocket_path) as websocket:
        websocket.receive_json()  # session_connected
        websocket.send_json({"type": "user_text", "text": "find dog food"})
        received = [websocket.receive_json() for _ in range(4)]
        names = {event["event"] for event in received}
        assert "checkpoint_required" in names


def test_live_websocket_interrupt_audio_and_cancel_flow(client: TestClient) -> None:
    payload = _create_live_session(client)
    websocket_path = payload["websocket_path"]

    with client.websocket_connect(websocket_path) as websocket:
        websocket.receive_json()  # session_connected

        websocket.send_json({"type": "interrupt"})
        interrupted = websocket.receive_json()
        assert interrupted["event"] == "interrupted"

        websocket.send_json(
            {
                "type": "audio_chunk",
                "audio_base64": "ZmFrZQ==",
                "transcript_hint": "search dog food",
            }
        )
        transcription = websocket.receive_json()
        assert transcription["event"] == "transcription"
        assert transcription["data"]["text"] == "search dog food"
        events = [websocket.receive_json() for _ in range(3)]
        names = {event["event"] for event in events}
        assert "agent_step" in names

        websocket.send_json({"type": "cancel"})
        cancelled = websocket.receive_json()
        assert cancelled["event"] == "agent_step"


def test_live_websocket_tts_failure_graceful(
    client: TestClient,
    fake_speech_provider: FakeSpeechProvider,
) -> None:
    fake_speech_provider.raise_on_synthesize = True
    payload = _create_live_session(client)
    websocket_path = payload["websocket_path"]

    with client.websocket_connect(websocket_path) as websocket:
        websocket.receive_json()  # session_connected
        websocket.send_json({"type": "user_text", "text": "find dog food"})
        events = [websocket.receive_json() for _ in range(3)]
        spoken = next(event for event in events if event["event"] == "spoken_output")
        assert spoken["data"]["provider"] in {"fake", "fallback-error"}


def test_live_websocket_localized_hi_in_spoken_output(client: TestClient) -> None:
    payload = _create_live_session(client)
    websocket_path = payload["websocket_path"]

    with client.websocket_connect(websocket_path) as websocket:
        websocket.receive_json()  # session_connected
        websocket.send_json({"type": "start", "locale": "hi-IN"})
        started = websocket.receive_json()
        assert started["event"] == "session_started"
        assert started["data"]["locale"] == "hi-IN"

        websocket.send_json({"type": "user_text", "text": "find dog food", "locale": "hi-IN"})
        events = [websocket.receive_json() for _ in range(3)]
        spoken = next(event for event in events if event["event"] == "spoken_output")
        assert spoken["data"]["locale"] == "hi-IN"
        assert spoken["data"]["text"].startswith("सारांश:")


def test_live_websocket_unsupported_locale_falls_back_to_en_in(client: TestClient) -> None:
    payload = _create_live_session(client)
    websocket_path = payload["websocket_path"]

    with client.websocket_connect(websocket_path) as websocket:
        websocket.receive_json()  # session_connected
        websocket.send_json({"type": "start", "locale": "ta-IN"})
        started = websocket.receive_json()
        assert started["event"] == "session_started"
        assert started["data"]["locale"] == "en-IN"


def test_live_websocket_checkpoint_response_resumes_state_machine(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    testing_session_local,
) -> None:
    payload = _create_live_session(client)
    session_id = payload["session_id"]
    _seed_live_control_state(
        testing_session_local,
        session_id=session_id,
        state_after="CHECKPOINT_SENSITIVE_ACTION",
        checkpoint=SensitiveCheckpointRequest(
            kind=SensitiveCheckpointKind.PAYMENT_CONFIRMATION,
            status=CheckpointStatus.PENDING,
            reason="Manual payment confirmation required.",
            prompt_to_user="Please approve the payment confirmation step.",
        ),
    )

    with client.websocket_connect(payload["websocket_path"]) as websocket:
        websocket.receive_json()  # session_connected
        pending = websocket.receive_json()
        assert pending["event"] == "checkpoint_required"
        websocket.send_json({"type": "checkpoint_response", "approved": True})
        events = [websocket.receive_json() for _ in range(3)]
        names = [event["event"] for event in events]
        assert names[0] == "checkpoint_resolved"
        agent_step = next(event for event in events if event["event"] == "agent_step")
        assert agent_step["data"]["new_state"] == "ASSISTED_MODE"
        assert any(call["method"] == "perform_checkout" for call in fake_browser_client.calls)


def test_live_websocket_final_confirmation_response_reaches_post_purchase_summary(
    client: TestClient,
    fake_browser_client: FakeBrowserRuntimeClient,
    testing_session_local,
) -> None:
    payload = _create_live_session(client)
    session_id = payload["session_id"]
    _seed_live_control_state(
        testing_session_local,
        session_id=session_id,
        state_after="FINAL_CONFIRMATION",
        final_confirmation=FinalPurchaseConfirmation(
            required=True,
            confirmed=False,
            prompt_to_user="Please confirm final purchase.",
            confirmation_phrase_expected="confirm purchase",
            notes="seeded final confirmation state",
        ),
    )

    with client.websocket_connect(payload["websocket_path"]) as websocket:
        websocket.receive_json()  # session_connected
        required = websocket.receive_json()
        assert required["event"] == "final_confirmation_required"
        websocket.send_json({"type": "final_confirmation_response", "approved": True})
        events = [websocket.receive_json() for _ in range(3)]
        names = [event["event"] for event in events]
        assert names[0] == "final_confirmation_resolved"
        agent_step = next(event for event in events if event["event"] == "agent_step")
        assert agent_step["data"]["new_state"] in {"ORDER_PLACED", "POST_PURCHASE_SUMMARY"}
        assert any(call["method"] == "finalize_purchase" for call in fake_browser_client.calls)

    context = client.get(f"/api/sessions/{session_id}/context")
    assert context.status_code == 200
    payload_json = context.json()
    assert payload_json["latest_final_purchase_confirmation"]["confirmed"] is True
    assert payload_json["latest_post_purchase_summary"] is not None
