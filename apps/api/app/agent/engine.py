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
    PostPurchaseObserved,
    RecoveryTriggered,
    ReviewAnalysisResult,
    SessionCloseRequested,
    ToolError,
    TrustCheckResult,
    UserIntentParsed,
    VerificationResult,
)
from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.review_analysis import ReviewConflictLevel
from app.schemas.trust_verification import TrustStatus


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

    if isinstance(event, RecoveryTriggered):
        recovery_command = AgentCommand(
            type=AgentCommandType.HANDLE_ERROR_RECOVERY,
            payload={"error_type": event.reason or "recovery_triggered"},
        )
        recovery_log = _build_log(
            session_id=session_id,
            step_type=AgentStepType.ERROR,
            state_before=current_state,
            state_after=AgentState.ERROR_RECOVERY,
            tool_name="agent.recovery",
            tool_input_excerpt="recovery_triggered",
            tool_output_excerpt=event.reason,
            error_type="recovery_triggered",
            error_message=event.reason,
            user_spoken_summary="I am running a recovery step to stabilize the flow.",
        )
        return AgentTransitionResult(
            new_state=AgentState.ERROR_RECOVERY,
            commands=[recovery_command],
            log_entries=[recovery_log],
            spoken_summary=recovery_log.user_spoken_summary,
            debug_notes="Recovery event routed to recovery state.",
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
            type=AgentCommandType.RUN_TRUST_CHECK,
            payload={"intent": event.intent, "query": event.query, "merchant": event.merchant},
        )
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.INTENT_PARSE,
            state_before=current_state,
            state_after=AgentState.TRUST_CHECK,
            tool_name="agent.intent_parser",
            tool_input_excerpt=event.intent,
            tool_output_excerpt="Intent captured and trust check started.",
            user_spoken_summary="Understood. I am validating trust signals before searching.",
        )
        return AgentTransitionResult(
            new_state=AgentState.TRUST_CHECK,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Session initialized from user intent.",
        )

    if current_state == AgentState.TRUST_CHECK and isinstance(event, TrustCheckResult):
        if event.status == TrustStatus.SUSPICIOUS:
            return _halt_transition(
                session_id=session_id,
                current_state=current_state,
                reason=event.reason or "Trust check flagged suspicious merchant signals.",
            )

        command = AgentCommand(
            type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS,
            payload={
                "query": event.query,
                "merchant": event.merchant,
            },
        )
        trust_note = "trusted"
        if event.status != TrustStatus.TRUSTED:
            trust_note = "unverified"
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.VERIFICATION,
            state_before=current_state,
            state_after=AgentState.SEARCHING_PRODUCTS,
            tool_name="agent.trust_gate",
            tool_input_excerpt=f"trust_status={event.status.value}",
            tool_output_excerpt=f"Trust gate passed ({trust_note}).",
            user_spoken_summary=(
                "Trust checks passed. Starting product search."
                if trust_note == "trusted"
                else "Trust checks are inconclusive, continuing with caution."
            ),
        )
        return AgentTransitionResult(
            new_state=AgentState.SEARCHING_PRODUCTS,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes=f"Trust gate passed with status {event.status.value}.",
        )

    if current_state == AgentState.SEARCHING_PRODUCTS and isinstance(event, NavResult):
        if event.success and (event.confidence is None or event.confidence >= 0.5):
            inspect_command = AgentCommand(
                type=AgentCommandType.INSPECT_PRODUCT_PAGE,
                payload={"page_type": event.page_type},
            )
            select_variant_command = AgentCommand(
                type=AgentCommandType.SELECT_PRODUCT_VARIANT,
                payload={},
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
                commands=[inspect_command, select_variant_command],
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
            command = AgentCommand(type=AgentCommandType.ANALYZE_REVIEWS)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.VERIFICATION,
                state_before=current_state,
                state_after=AgentState.REVIEW_ANALYSIS,
                tool_name="agent.verifier",
                tool_input_excerpt="product_and_variant_check",
                tool_output_excerpt="Verification passed and review analysis requested.",
                user_spoken_summary="Product and variant checks passed. Running review analysis.",
            )
            return AgentTransitionResult(
                new_state=AgentState.REVIEW_ANALYSIS,
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

    if current_state == AgentState.REVIEW_ANALYSIS and isinstance(event, ReviewAnalysisResult):
        if event.requires_user_confirmation or event.conflict_level in {
            ReviewConflictLevel.MEDIUM,
            ReviewConflictLevel.HIGH,
        }:
            command = AgentCommand(type=AgentCommandType.REQUEST_HUMAN_CHECKPOINT)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.VERIFICATION,
                state_before=current_state,
                state_after=AgentState.ASSISTED_MODE,
                tool_name="agent.review_gate",
                tool_input_excerpt=f"review_conflict={event.conflict_level.value}",
                tool_output_excerpt=event.notes or "Review ambiguity requires human confirmation.",
                human_checkpoint=True,
                user_spoken_summary=(
                    "Review signals are ambiguous. I need your confirmation before checkout."
                ),
            )
            return AgentTransitionResult(
                new_state=AgentState.ASSISTED_MODE,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Review gate routed to assisted mode.",
            )

        add_to_cart_command = AgentCommand(type=AgentCommandType.ADD_TO_CART)
        review_cart_command = AgentCommand(type=AgentCommandType.REVIEW_CART)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.VERIFICATION,
            state_before=current_state,
            state_after=AgentState.CART_VERIFICATION,
            tool_name="agent.review_gate",
            tool_input_excerpt=f"review_conflict={event.conflict_level.value}",
            tool_output_excerpt=event.notes or "Review signals acceptable for cart verification.",
            user_spoken_summary="Review signals look acceptable. Moving to cart verification.",
        )
        return AgentTransitionResult(
            new_state=AgentState.CART_VERIFICATION,
            commands=[add_to_cart_command, review_cart_command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Review gate passed.",
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
            command = AgentCommand(type=AgentCommandType.REQUEST_FINAL_CONFIRMATION)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.FINAL_CONFIRMATION,
                tool_name="agent.checkout_planner",
                tool_input_excerpt="checkout_completed",
                tool_output_excerpt="Checkout completed; awaiting final confirmation.",
                human_checkpoint=True,
                user_spoken_summary="Checkout is complete. Please confirm final purchase.",
            )
            return AgentTransitionResult(
                new_state=AgentState.FINAL_CONFIRMATION,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Checkout completed; final confirmation required.",
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

    if current_state == AgentState.ASSISTED_MODE and isinstance(event, CheckoutProgress):
        if event.low_confidence:
            return _halt_transition(
                session_id=session_id,
                current_state=current_state,
                reason="Assisted mode entered low confidence.",
            )

        if event.completed:
            command = AgentCommand(type=AgentCommandType.REQUEST_FINAL_CONFIRMATION)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.FINAL_CONFIRMATION,
                tool_name="agent.assisted_mode",
                tool_input_excerpt="assisted_checkout_completed",
                tool_output_excerpt="Awaiting final confirmation.",
                human_checkpoint=True,
                user_spoken_summary="Assisted checkout step completed. Please confirm final purchase.",
            )
            return AgentTransitionResult(
                new_state=AgentState.FINAL_CONFIRMATION,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Assisted mode moved to final confirmation.",
            )

        if event.proceed_to_checkout:
            command = AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.CHECKOUT_FLOW,
                tool_name="agent.assisted_mode",
                tool_input_excerpt="resume_checkout_after_assist",
                tool_output_excerpt="Checkout resumed.",
                human_checkpoint=True,
                user_spoken_summary="Resuming checkout in assisted mode.",
            )
            return AgentTransitionResult(
                new_state=AgentState.CHECKOUT_FLOW,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Assisted mode resumed checkout.",
            )

        command = AgentCommand(type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.NAVIGATION,
            state_before=current_state,
            state_after=AgentState.SEARCHING_PRODUCTS,
            tool_name="agent.assisted_mode",
            tool_input_excerpt="return_to_search_from_assisted",
            tool_output_excerpt="Returned to search.",
            user_spoken_summary="Returning to search from assisted mode.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SEARCHING_PRODUCTS,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Assisted mode redirected to search.",
        )

    if current_state == AgentState.ASSISTED_MODE and isinstance(event, NavResult):
        if event.success:
            command = AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.NAVIGATION,
                state_before=current_state,
                state_after=AgentState.CHECKOUT_FLOW,
                tool_name="agent.assisted_mode",
                tool_input_excerpt="assisted_navigation_success",
                tool_output_excerpt="Checkout resumed after assisted navigation.",
                human_checkpoint=True,
                user_spoken_summary="Assisted navigation succeeded. Continuing checkout.",
            )
            return AgentTransitionResult(
                new_state=AgentState.CHECKOUT_FLOW,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Assisted mode navigation succeeded.",
            )
        return _halt_transition(
            session_id=session_id,
            current_state=current_state,
            reason="Assisted mode navigation did not stabilize.",
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
                state_after=AgentState.ASSISTED_MODE,
                tool_name="agent.checkpoint",
                tool_input_excerpt="checkpoint_approved",
                tool_output_excerpt="Entering assisted mode after checkpoint approval.",
                human_checkpoint=True,
                user_spoken_summary="Checkpoint completed. Entering assisted mode.",
            )
            return AgentTransitionResult(
                new_state=AgentState.ASSISTED_MODE,
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

    if current_state == AgentState.FINAL_CONFIRMATION and isinstance(
        event, HumanCheckpointResolved
    ):
        if event.approved:
            command = AgentCommand(type=AgentCommandType.MARK_ORDER_PLACED)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.CHECKOUT,
                state_before=current_state,
                state_after=AgentState.ORDER_PLACED,
                tool_name="agent.final_confirmation",
                tool_input_excerpt="final_confirmation_approved",
                tool_output_excerpt="Order marked placed.",
                human_checkpoint=True,
                user_spoken_summary="Final confirmation approved. Marking order as placed.",
            )
            return AgentTransitionResult(
                new_state=AgentState.ORDER_PLACED,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Final confirmation approved.",
            )

        command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.CHECKOUT,
            state_before=current_state,
            state_after=AgentState.SESSION_CLOSING,
            tool_name="agent.final_confirmation",
            tool_input_excerpt="final_confirmation_rejected",
            tool_output_excerpt="Session closing requested after final confirmation rejection.",
            human_checkpoint=True,
            user_spoken_summary="Final confirmation was not approved. Closing safely.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SESSION_CLOSING,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Final confirmation rejected.",
        )

    if current_state == AgentState.ORDER_PLACED and isinstance(event, PostPurchaseObserved):
        if event.detected:
            command = AgentCommand(type=AgentCommandType.SUMMARIZE_POST_PURCHASE)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.META,
                state_before=current_state,
                state_after=AgentState.POST_PURCHASE_SUMMARY,
                tool_name="agent.post_purchase",
                tool_input_excerpt="post_purchase_detected",
                tool_output_excerpt=event.notes or "Post-purchase evidence detected.",
                user_spoken_summary="Order appears placed. I will summarize post-purchase details.",
            )
            return AgentTransitionResult(
                new_state=AgentState.POST_PURCHASE_SUMMARY,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="Post-purchase evidence detected.",
            )

        command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.META,
            state_before=current_state,
            state_after=AgentState.SESSION_CLOSING,
            tool_name="agent.post_purchase",
            tool_input_excerpt="post_purchase_not_detected",
            tool_output_excerpt=event.notes or "No post-purchase evidence; closing session.",
            user_spoken_summary="Closing the session after final confirmation.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SESSION_CLOSING,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="No post-purchase evidence detected.",
        )

    if current_state == AgentState.ERROR_RECOVERY and isinstance(event, NavResult):
        if event.success:
            command = AgentCommand(type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.NAVIGATION,
                state_before=current_state,
                state_after=AgentState.UI_STABILIZING,
                tool_name="agent.recovery",
                tool_input_excerpt="recovery_retry_success",
                tool_output_excerpt="Recovered and moved to UI stabilization.",
                user_spoken_summary="Recovery succeeded. Stabilizing the UI before resuming search.",
            )
            return AgentTransitionResult(
                new_state=AgentState.UI_STABILIZING,
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

    if current_state == AgentState.UI_STABILIZING and isinstance(event, NavResult):
        if event.success and (event.confidence is None or event.confidence >= 0.4):
            command = AgentCommand(type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS)
            log_entry = _build_log(
                session_id=session_id,
                step_type=AgentStepType.NAVIGATION,
                state_before=current_state,
                state_after=AgentState.SEARCHING_PRODUCTS,
                tool_name="agent.ui_stabilizer",
                tool_input_excerpt="ui_stable",
                tool_output_excerpt="UI stabilization complete; resumed search.",
                user_spoken_summary="UI stabilized. Resuming search.",
            )
            return AgentTransitionResult(
                new_state=AgentState.SEARCHING_PRODUCTS,
                commands=[command],
                log_entries=[log_entry],
                spoken_summary=log_entry.user_spoken_summary,
                debug_notes="UI stabilization complete.",
            )

        command = AgentCommand(
            type=AgentCommandType.HANDLE_ERROR_RECOVERY,
            payload={"error_type": "ui_stabilization_failed"},
        )
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.ERROR,
            state_before=current_state,
            state_after=AgentState.ERROR_RECOVERY,
            tool_name="agent.ui_stabilizer",
            tool_input_excerpt="ui_stabilization_failed",
            tool_output_excerpt="UI stabilization failed; returning to recovery.",
            error_type="ui_stabilization_failed",
            error_message="UI stabilization failed.",
            user_spoken_summary="UI stabilization failed. Returning to recovery.",
        )
        return AgentTransitionResult(
            new_state=AgentState.ERROR_RECOVERY,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="UI stabilization failed.",
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

    if current_state == AgentState.POST_PURCHASE_SUMMARY and isinstance(
        event, SessionCloseRequested
    ):
        command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.META,
            state_before=current_state,
            state_after=AgentState.SESSION_CLOSING,
            tool_name="agent.post_purchase",
            tool_input_excerpt="close_after_post_purchase",
            tool_output_excerpt="Session closing after post-purchase summary.",
            user_spoken_summary="Post-purchase summary complete. Closing session.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SESSION_CLOSING,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Close requested after post-purchase summary.",
        )

    if current_state == AgentState.FINAL_CONFIRMATION and isinstance(
        event, SessionCloseRequested
    ):
        command = AgentCommand(type=AgentCommandType.CLOSE_SESSION)
        log_entry = _build_log(
            session_id=session_id,
            step_type=AgentStepType.META,
            state_before=current_state,
            state_after=AgentState.SESSION_CLOSING,
            tool_name="agent.final_confirmation",
            tool_input_excerpt="close_requested_at_final_confirmation",
            tool_output_excerpt="Session closing requested.",
            user_spoken_summary="Final confirmation cancelled. Closing session.",
        )
        return AgentTransitionResult(
            new_state=AgentState.SESSION_CLOSING,
            commands=[command],
            log_entries=[log_entry],
            spoken_summary=log_entry.user_spoken_summary,
            debug_notes="Close requested at final confirmation.",
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
