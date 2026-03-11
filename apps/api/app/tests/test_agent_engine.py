from uuid import uuid4

import pytest

from app.agent.engine import next_state
from app.agent.state import (
    AgentCommandType,
    AgentState,
    CheckoutProgress,
    HumanCheckpointResolved,
    LowConfidenceTriggered,
    NavResult,
    PostPurchaseObserved,
    ReviewAnalysisResult,
    TrustCheckResult,
    UserIntentParsed,
    VerificationResult,
)
from app.schemas.agent_log import AgentStepType
from app.schemas.review_analysis import ReviewConflictLevel
from app.schemas.session import Merchant
from app.schemas.trust_verification import TrustStatus


def test_init_to_trust_check_transition() -> None:
    session_id = uuid4()
    event = UserIntentParsed(
        intent="search_products",
        query="dog food",
        merchant=Merchant.AMAZON,
    )

    result = next_state(AgentState.SESSION_INITIALIZING, event, session_id)

    assert result.new_state == AgentState.TRUST_CHECK
    assert result.commands[0].type == AgentCommandType.RUN_TRUST_CHECK
    assert result.log_entries[0].step_type == AgentStepType.INTENT_PARSE
    assert result.log_entries[0].state_before == AgentState.SESSION_INITIALIZING.value
    assert result.log_entries[0].state_after == AgentState.TRUST_CHECK.value


def test_trust_check_transitions_to_search() -> None:
    session_id = uuid4()
    event = TrustCheckResult(status=TrustStatus.TRUSTED)

    result = next_state(AgentState.TRUST_CHECK, event, session_id)

    assert result.new_state == AgentState.SEARCHING_PRODUCTS
    assert result.commands[0].type == AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS
    assert result.log_entries[0].step_type == AgentStepType.VERIFICATION


def test_checkout_requires_human_checkpoint() -> None:
    session_id = uuid4()
    event = CheckoutProgress(sensitive_step_required=True)

    result = next_state(AgentState.CHECKOUT_FLOW, event, session_id)

    assert result.new_state == AgentState.CHECKPOINT_SENSITIVE_ACTION
    assert result.commands[0].type == AgentCommandType.REQUEST_HUMAN_CHECKPOINT
    assert result.log_entries[0].human_checkpoint is True
    assert result.log_entries[0].step_type == AgentStepType.CHECKOUT


def test_review_analysis_routes_to_assisted_mode_on_conflict() -> None:
    session_id = uuid4()
    event = ReviewAnalysisResult(
        conflict_level=ReviewConflictLevel.HIGH,
        requires_user_confirmation=True,
    )

    result = next_state(AgentState.REVIEW_ANALYSIS, event, session_id)

    assert result.new_state == AgentState.ASSISTED_MODE
    assert result.commands[0].type == AgentCommandType.REQUEST_HUMAN_CHECKPOINT
    assert result.log_entries[0].human_checkpoint is True


def test_review_analysis_low_conflict_routes_to_add_to_cart_and_cart_review() -> None:
    session_id = uuid4()
    event = ReviewAnalysisResult(
        conflict_level=ReviewConflictLevel.LOW,
        requires_user_confirmation=False,
    )

    result = next_state(AgentState.REVIEW_ANALYSIS, event, session_id)

    assert result.new_state == AgentState.CART_VERIFICATION
    assert [command.type for command in result.commands] == [
        AgentCommandType.ADD_TO_CART,
        AgentCommandType.REVIEW_CART,
    ]


def test_checkout_completion_requires_final_confirmation() -> None:
    session_id = uuid4()
    event = CheckoutProgress(completed=True)

    result = next_state(AgentState.CHECKOUT_FLOW, event, session_id)

    assert result.new_state == AgentState.FINAL_CONFIRMATION
    assert result.commands[0].type == AgentCommandType.REQUEST_FINAL_CONFIRMATION
    assert result.log_entries[0].human_checkpoint is True
    assert result.spoken_summary == "Checkout entry reached. Stopping before guest checkout."
    assert "stopping before guest checkout" in (result.log_entries[0].tool_output_excerpt or "").lower()


@pytest.mark.skip(reason="Deferred full-checkout/post-purchase transition outside bounded Phase 2 nopCommerce flow.")
def test_final_confirmation_approval_moves_to_order_placed() -> None:
    session_id = uuid4()

    result = next_state(
        AgentState.FINAL_CONFIRMATION,
        HumanCheckpointResolved(approved=True),
        session_id,
    )

    assert result.new_state == AgentState.ORDER_PLACED
    assert result.commands[0].type == AgentCommandType.MARK_ORDER_PLACED
    assert result.log_entries[0].step_type == AgentStepType.CHECKOUT


@pytest.mark.skip(reason="Deferred post-purchase transition outside bounded Phase 2 nopCommerce flow.")
def test_order_placed_post_purchase_detected_moves_to_post_purchase_summary() -> None:
    session_id = uuid4()
    event = PostPurchaseObserved(detected=True)

    result = next_state(AgentState.ORDER_PLACED, event, session_id)

    assert result.new_state == AgentState.POST_PURCHASE_SUMMARY
    assert result.commands[0].type == AgentCommandType.SUMMARIZE_POST_PURCHASE
    assert result.log_entries[0].step_type == AgentStepType.META


def test_low_confidence_event_halts_from_any_state() -> None:
    session_id = uuid4()
    event = LowConfidenceTriggered(reason="insufficient certainty on page meaning")

    result = next_state(AgentState.SEARCHING_PRODUCTS, event, session_id)

    assert result.new_state == AgentState.LOW_CONFIDENCE_HALT
    assert result.log_entries[0].low_confidence is True
    assert "insufficient certainty" in (result.debug_notes or "")


def test_unsupported_transition_goes_to_low_confidence_halt() -> None:
    session_id = uuid4()
    event = UserIntentParsed(query="sports shoes")

    result = next_state(AgentState.VIEWING_PRODUCT_DETAIL, event, session_id)

    assert result.new_state == AgentState.LOW_CONFIDENCE_HALT
    assert result.commands[0].type == AgentCommandType.HALT_LOW_CONFIDENCE
    assert result.log_entries[0].low_confidence is True
    assert result.log_entries[0].step_type == AgentStepType.ERROR


def test_search_nav_success_opens_product_detail() -> None:
    session_id = uuid4()
    event = NavResult(success=True, confidence=0.9, page_type="search_results")

    result = next_state(AgentState.SEARCHING_PRODUCTS, event, session_id)

    assert result.new_state == AgentState.VIEWING_PRODUCT_DETAIL
    assert result.commands[0].type == AgentCommandType.INSPECT_PRODUCT_PAGE
    assert result.log_entries[0].step_type == AgentStepType.NAVIGATION


def test_verification_routes_to_review_analysis() -> None:
    session_id = uuid4()
    event = VerificationResult(success=True)

    result = next_state(AgentState.VIEWING_PRODUCT_DETAIL, event, session_id)

    assert result.new_state == AgentState.REVIEW_ANALYSIS
    assert result.commands[0].type == AgentCommandType.ANALYZE_REVIEWS
