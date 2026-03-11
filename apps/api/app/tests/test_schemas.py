from datetime import datetime
from uuid import UUID, uuid4

from app.schemas import (
    AgentLogEntry,
    AgentStepType,
    Merchant,
    SessionCreate,
    SessionDetail,
    SessionStatus,
    SessionSummary,
)


def test_session_create_defaults() -> None:
    payload = SessionCreate()

    assert payload.merchant == Merchant.DEMO_STORE
    assert payload.locale is None
    assert payload.screen_reader is None
    assert payload.client_version is None
    assert payload.user_agent is None


def test_session_summary_and_detail_contracts() -> None:
    summary = SessionSummary(merchant=Merchant.DEMO_STORE, status=SessionStatus.ACTIVE)
    detail = SessionDetail(
        merchant=Merchant.FLIPKART,
        status=SessionStatus.ENDED,
        locale="en-IN",
        screen_reader="VoiceOver",
        client_version="0.1.0",
    )

    assert summary.status in SessionStatus
    assert isinstance(summary.session_id, UUID)
    assert isinstance(summary.created_at, datetime)

    assert detail.status in SessionStatus
    assert isinstance(detail.session_id, UUID)
    assert isinstance(detail.created_at, datetime)
    assert detail.locale == "en-IN"


def test_agent_log_entry_contract() -> None:
    session_id = uuid4()
    entry = AgentLogEntry(
        session_id=session_id,
        step_type=AgentStepType.NAVIGATION,
        state_before="SEARCH",
        state_after="PRODUCT",
        low_confidence=True,
        human_checkpoint=True,
        tool_name="playwright.navigate",
        tool_input_excerpt="Navigate to first product card",
        tool_output_excerpt="Navigation completed",
    )

    assert entry.session_id == session_id
    assert entry.step_type == AgentStepType.NAVIGATION
    assert entry.low_confidence is True
    assert entry.human_checkpoint is True
    assert isinstance(entry.id, UUID)
    assert isinstance(entry.created_at, datetime)
