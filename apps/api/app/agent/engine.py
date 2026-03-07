from __future__ import annotations

from uuid import UUID

from app.agent.state import (
    AgentCommand,
    AgentCommandType,
    AgentEvent,
    AgentState,
    AgentTransitionResult,
    CheckoutProgress,
    HumanCheckpointResolved,
    LowConfidenceTriggered,
    NavResult,
    SessionCloseRequested,
    ToolError,
    UserIntentParsed,
    VerificationResult,
)
from app.schemas.agent_log import AgentLogEntry, AgentStepType


def _build_log(
    *,
    session_id: UUID,
    step_type: AgentStepType,
    state_before: AgentState,
    state_after: AgentState,
    tool_name: str | None = None,
    tool_input_excerpt: str | None = None,
    tool_output_excerpt: str | None = None,
    low_confidence: bool = False,
    human_checkpoint: bool = False,
    user_spoken_summary: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> AgentLogEntry:
    return AgentLogEntry(
        session_id=session_id,
        step_type=step_type,
        state_before=state_before.value,
        state_after=state_after.value,
        tool_name=tool_name,
        tool_input_excerpt=tool_input_excerpt,
        tool_output_excerpt=tool_output_excerpt,
        low_confidence=low_confidence,
        human_checkpoint=human_checkpoint,
        user_spoken_summary=user_spoken_summary,
        error_type=error_type,
        error_message=error_message,
    )


def _halt_transition(
    *,
    session_id: UUID,
    current_state: AgentState,
    reason: str,
) -> AgentTransitionResult:
    command = AgentCommand(
        type=AgentCommandType.HALT_LOW_CONFIDENCE,
        payload={"reason": reason},
    )
    log_entry = _build_log(
        session_id=session_id,
        step_type=AgentStepType.ERROR,
        state_before=current_state,
        state_after=AgentState.LOW_CONFIDENCE_HALT,
        tool_name="agent.state_machine",
        tool_input_excerpt="low_confidence_halt",
        tool_output_excerpt=reason,
        low_confidence=True,
        user_spoken_summary="I am not confident enough to continue safely.",
        error_type="low_confidence_halt",
        error_message=reason,
    )
    return AgentTransitionResult(
        new_state=AgentState.LOW_CONFIDENCE_HALT,
        commands=[command],
        log_entries=[log_entry],
        spoken_summary=log_entry.user_spoken_summary,
        debug_notes=reason,
    )


def next_state(
    current_state: AgentState,
    event: AgentEvent,
    session_id: UUID,
) -> AgentTransitionResult:
    if isinstance(event, LowConfidenceTriggered):
        return _halt_transition(
            session_id=session_id,
            current_state=current_state,
            reason=event.reason or "Low confidence was triggered.",
        )

    if isinstance(event, ToolError):
        error_command = AgentCommand(
            type=AgentCommandType.HANDLE_ERROR_RECOVERY,
            payload={"error_type": event.error_type},
        )
        error_log = _build_log(
            session_id=session_id,
            step_type=AgentStepType.ERROR,
            state_before=current_state,
            state_after=AgentState.ERROR_RECOVERY,
            tool_name="agent.tool_adapter",
            tool_input_excerpt="tool_error",
            tool_output_excerpt=event.error_message,
            error_type=event.error_type,
            error_message=event.error_message,
            user_spoken_summary="I hit a tool error and I am entering recovery.",
        )
        return AgentTransitionResult(
            new_state=AgentState.ERROR_RECOVERY,
            commands=[error_command],
            log_entries=[error_log],
            spoken_summary=error_log.user_spoken_summary,
            debug_notes="Tool error routed to recovery.",
        )

    if current_state == AgentState.DONE:
        done_log = _build_log(
            session_id=session_id,
            step_type=AgentStepType.META,
            state_before=AgentState.DONE,
            state_after=AgentState.DONE,
            tool_name="agent.state_machine",
            user_spoken_summary="Session is already closed.",
        )
        return AgentTransitionResult(
            new_state=AgentState.DONE,
            commands=[],
            log_entries=[done_log],
            spoken_summary=done_log.user_spoken_summary,
            debug_notes="No transition from DONE.",
        )

    if current_state == AgentState.SESSION_INITIALIZING and isinstance(event, UserIntentParsed):
        command = AgentCommand(
            type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS,
            payload={"intent": event.intent, "query": event.query, "merchant": event.merchant},
        )
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.INTENT_PARSE,
            state_before=current_state,
            state_after=AgentState.SEARCHING_PRODUCTS,
            tool_name="agent.intent_parser",
            tool_input_excerpt=event.intent,
            tool_output_excerpt="Intent captured and search started.",
            user_spoken_summary="Understood. I am searching products now.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SEARCHING_PRODUCTS,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Session initialized from user intent.",
        )

    if current_state == AgentState.SEARCHING_PRODUCTS and isinstance(event, NavResult):
        if event.success and (event.confidence is None or event.confidence >= 0.5):
            command = AgentCommand(
                type=AgentCommandType.INSPECT_PRODUCT_PAGE,
                payload={"page_type": event.page_type},
            )
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.NAVIGATION,
                state_before=current_state,
                state_after=AgentState.VIEWING_PRODUCT_DETAIL,
                tool_name="agent.navigator",
                tool_input_excerpt="search_results_navigation",
                tool_output_excerpt="Candidate product opened.",
                user_spoken_summary="I found candidates and opened a product detail page.",
            )
            return AgentTransitionResult(
                new_state=AgentState.VIEWING_PRODUCT_DETAIL,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Search to product detail transition.",
            )

        return _halt_transition(
            session_id=session_id,
            current_state=current_state,
            reason="Navigation from search results was uncertain.",
        )

    if current_state == AgentState.VIEWING_PRODUCT_DETAIL and isinstance(event, VerificationResult):
        if event.success and not event.low_confidence:
            command = AgentCommand(type=AgentCommandType.REVIEW_CART)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.VERIFICATION,
                state_before=current_state,
                state_after=AgentState.CART_VERIFICATION,
                tool_name="agent.verifier",
                tool_input_excerpt="product_and_variant_check",
                tool_output_excerpt="Verification passed.",
                user_spoken_summary="Product and variant checks passed. Reviewing cart.",
            )
            return AgentTransitionResult(
                new_state=AgentState.CART_VERIFICATION,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Product verification succeeded.",
            )

        return _halt_transition(
            session_id=session_id,
            current_state=current_state,
            reason=event.notes or "Verification failed or was low confidence.",
        )

    if current_state == AgentState.CART_VERIFICATION and isinstance(event, CheckoutProgress):
        if event.low_confidence:
            return _halt_transition(
                session_id=session_id,
                current_state=current_state,
                reason="Cart verification entered low confidence.",
            )

        if event.proceed_to_checkout:
            command = AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.CHECKOUT_FLOW,
                tool_name="agent.checkout_planner",
                tool_input_excerpt="proceed_to_checkout",
                tool_output_excerpt="Checkout flow started.",
                user_spoken_summary="Cart looks ready. Moving to checkout.",
            )
            return AgentTransitionResult(
                new_state=AgentState.CHECKOUT_FLOW,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Cart verification to checkout flow.",
            )

        command = AgentCommand(type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.NAVIGATION,
            state_before=current_state,
            state_after=AgentState.SEARCHING_PRODUCTS,
            tool_name="agent.navigator",
            tool_input_excerpt="search_more_products",
            tool_output_excerpt="Returned to search.",
            user_spoken_summary="Returning to search for more items.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SEARCHING_PRODUCTS,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Cart verification redirected to search.",
        )

    if current_state == AgentState.CHECKOUT_FLOW and isinstance(event, CheckoutProgress):
        if event.low_confidence:
            return _halt_transition(
                session_id=session_id,
                current_state=current_state,
                reason="Checkout became unsafe due to low confidence.",
            )

        if event.sensitive_step_required:
            command = AgentCommand(type=AgentCommandType.REQUEST_HUMAN_CHECKPOINT)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.CHECKPOINT_SENSITIVE_ACTION,
                tool_name="agent.checkpoint",
                tool_input_excerpt="sensitive_step_detected",
                tool_output_excerpt="Human checkpoint required.",
                human_checkpoint=True,
                user_spoken_summary="A sensitive step needs your direct action.",
            )
            return AgentTransitionResult(
                new_state=AgentState.CHECKPOINT_SENSITIVE_ACTION,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Checkout checkpoint required.",
            )

        if event.completed:
            command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.SESSION_CLOSING,
                tool_name="agent.checkout_planner",
                tool_input_excerpt="checkout_completed",
                tool_output_excerpt="Closing session.",
                user_spoken_summary="Checkout flow is complete. Closing session.",
            )
            return AgentTransitionResult(
                new_state=AgentState.SESSION_CLOSING,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Checkout completed.",
            )

        continue_command = AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT)
        continue_log = _build_log(
            session_id=session_id,
            step_type=AgentStepType.CHECKOUT,
            state_before=current_state,
            state_after=AgentState.CHECKOUT_FLOW,
            tool_name="agent.checkout_planner",
            tool_input_excerpt="checkout_continue",
            tool_output_excerpt="Checkout continued.",
            user_spoken_summary="Continuing checkout.",
        )
        return AgentTransitionResult(
            new_state=AgentState.CHECKOUT_FLOW,
            commands=[continue_command],
            log_entries=[continue_log],
            spoken_summary=continue_log.user_spoken_summary,
            debug_notes="Checkout loop iteration.",
        )

    if current_state == AgentState.CHECKPOINT_SENSITIVE_ACTION and isinstance(
        event, HumanCheckpointResolved
    ):
        if event.approved:
            command = AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.CHECKOUT_FLOW,
                tool_name="agent.checkpoint",
                tool_input_excerpt="checkpoint_approved",
                tool_output_excerpt="Resuming checkout.",
                human_checkpoint=True,
                user_spoken_summary="Checkpoint completed. Resuming checkout.",
            )
            return AgentTransitionResult(
                new_state=AgentState.CHECKOUT_FLOW,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Checkpoint approved.",
            )

        command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.CHECKOUT,
            state_before=current_state,
            state_after=AgentState.SESSION_CLOSING,
            tool_name="agent.checkpoint",
            tool_input_excerpt="checkpoint_declined",
            tool_output_excerpt="Session closing requested by user.",
            human_checkpoint=True,
            user_spoken_summary="Checkpoint not approved. Closing session safely.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SESSION_CLOSING,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Checkpoint declined.",
        )

    if current_state == AgentState.ERROR_RECOVERY and isinstance(event, NavResult):
        if event.success:
            command = AgentCommand(type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.NAVIGATION,
                state_before=current_state,
                state_after=AgentState.SEARCHING_PRODUCTS,
                tool_name="agent.recovery",
                tool_input_excerpt="recovery_retry_success",
                tool_output_excerpt="Recovered and resumed search.",
                user_spoken_summary="Recovered from the error and resumed search.",
            )
            return AgentTransitionResult(
                new_state=AgentState.SEARCHING_PRODUCTS,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Recovery succeeded.",
            )

        return _halt_transition(
            session_id=session_id,
            current_state=current_state,
            reason="Recovery retry failed.",
        )

    if current_state == AgentState.LOW_CONFIDENCE_HALT and isinstance(
        event, SessionCloseRequested
    ):
        command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.META,
            state_before=current_state,
            state_after=AgentState.SESSION_CLOSING,
            tool_name="agent.state_machine",
            tool_input_excerpt="close_after_halt",
            tool_output_excerpt="Closing after low-confidence halt.",
            user_spoken_summary="Stopping now and closing the session.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SESSION_CLOSING,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Close requested from low-confidence halt.",
        )

    if current_state == AgentState.SESSION_CLOSING and isinstance(event, SessionCloseRequested):
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.META,
            state_before=current_state,
            state_after=AgentState.DONE,
            tool_name="agent.state_machine",
            tool_input_excerpt="session_closed",
            tool_output_excerpt="Session completed.",
            user_spoken_summary="Session complete.",
        )
        return AgentTransitionResult(
            new_state=AgentState.DONE,
            commands=[],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Session marked done.",
        )

    return _halt_transition(
        session_id=session_id,
        current_state=current_state,
        reason=(
            f"Unsupported transition from {current_state.value} "
            f"with event {event.event_type}."
        ),
    )
