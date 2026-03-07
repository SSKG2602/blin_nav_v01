from uuid import uuid4

from app.agent.engine import next_state
from app.agent.state import (
    AgentCommandType,
    AgentState,
    CheckoutProgress,
    LowConfidenceTriggered,
    NavResult,
    UserIntentParsed,
)
from app.schemas.agent_log import AgentStepType
from app.schemas.session import Merchant


def test_init_to_search_transition() -> None:
    session_id = uuid4()
    event = UserIntentParsed(
        intent="search_products",
        query="dog food",
        merchant=Merchant.AMAZON,
    )

    result = next_state(AgentState.SESSION_INITIALIZING, event, session_id)

    assert result.new_state == AgentState.SEARCHING_PRODUCTS
    assert result.commands[0].type == AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS
    assert result.log_entries[0].step_type == AgentStepType.INTENT_PARSE
    assert result.log_entries[0].state_before == AgentState.SESSION_INITIALIZING.value
    assert result.log_entries[0].state_after == AgentState.SEARCHING_PRODUCTS.value


def test_checkout_requires_human_checkpoint() -> None:
    session_id = uuid4()
    event = CheckoutProgress(sensitive_step_required=True)

    result = next_state(AgentState.CHECKOUT_FLOW, event, session_id)

    assert result.new_state == AgentState.CHECKPOINT_SENSITIVE_ACTION
    assert result.commands[0].type == AgentCommandType.REQUEST_HUMAN_CHECKPOINT
    assert result.log_entries[0].human_checkpoint is True
    assert result.log_entries[0].step_type == AgentStepType.CHECKOUT


def test_unsupported_transition_goes_to_low_confidence_halt() -> None:
    session_id = uuid4()
    event = UserIntentParsed(query="sports shoes")

    result = next_state(AgentState.VIEWING_PRODUCT_DETAIL, event, session_id)

    assert result.new_state == AgentState.LOW_CONFIDENCE_HALT
    assert result.commands[0].type == AgentCommandType.HALT_LOW_CONFIDENCE
    assert result.log_entries[0].low_confidence is True
    assert result.log_entries[0].step_type == AgentStepType.ERROR


def test_low_confidence_event_halts_from_any_state() -> None:
    session_id = uuid4()
    event = LowConfidenceTriggered(reason="insufficient certainty on page meaning")

    result = next_state(AgentState.SEARCHING_PRODUCTS, event, session_id)

    assert result.new_state == AgentState.LOW_CONFIDENCE_HALT
    assert result.log_entries[0].low_confidence is True
    assert "insufficient certainty" in (result.debug_notes or "")


def test_search_nav_success_opens_product_detail() -> None:
    session_id = uuid4()
    event = NavResult(success=True, confidence=0.9, page_type="search_results")

    result = next_state(AgentState.SEARCHING_PRODUCTS, event, session_id)

    assert result.new_state == AgentState.VIEWING_PRODUCT_DETAIL
    assert result.commands[0].type == AgentCommandType.INSPECT_PRODUCT_PAGE
    assert result.log_entries[0].step_type == AgentStepType.NAVIGATION
