from __future__ import annotations

from datetime import datetime

from app.schemas.agent_log import AgentLogEntry, AgentStepType
from app.schemas.clarification import ClarificationStatus
from app.schemas.review_analysis import ReviewConflictLevel
from app.schemas.session_closure import (
    ClosureAction,
    ClosureCheckpointEntry,
    FinalSelfDiagnosis,
    FinalSessionArtifact,
)
from app.schemas.session_context import SessionContextSnapshot


def _safe_text(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _checkpoint_history(context: SessionContextSnapshot) -> list[ClosureCheckpointEntry]:
    entries: list[ClosureCheckpointEntry] = []

    if context.latest_sensitive_checkpoint is not None:
        entries.append(
            ClosureCheckpointEntry(
                kind=context.latest_sensitive_checkpoint.kind.value,
                status=context.latest_sensitive_checkpoint.status.value,
                prompt_to_user=context.latest_sensitive_checkpoint.prompt_to_user,
                resolution_notes=context.latest_sensitive_checkpoint.resolution_notes,
                resolved_at=context.latest_sensitive_checkpoint.resolved_at,
            )
        )

    if context.latest_final_purchase_confirmation is not None:
        entries.append(
            ClosureCheckpointEntry(
                kind="FINAL_PURCHASE_CONFIRMATION",
                status="APPROVED" if context.latest_final_purchase_confirmation.confirmed else "PENDING",
                prompt_to_user=context.latest_final_purchase_confirmation.prompt_to_user,
                resolution_notes=context.latest_final_purchase_confirmation.notes,
                resolved_at=context.updated_at,
            )
        )

    return entries


def _important_actions(logs: list[AgentLogEntry]) -> list[ClosureAction]:
    actions: list[ClosureAction] = []
    for entry in logs[-8:]:
        summary = (
            _safe_text(entry.user_spoken_summary)
            or _safe_text(entry.tool_output_excerpt)
            or _safe_text(entry.error_message)
        )
        if not summary:
            continue
        actions.append(
            ClosureAction(
                state=entry.state_after or entry.state_before or "UNKNOWN",
                summary=summary,
                created_at=entry.created_at,
            )
        )
    return actions


def build_final_session_artifact(
    *,
    context: SessionContextSnapshot,
    logs: list[AgentLogEntry],
) -> FinalSessionArtifact:
    latest_intent = context.latest_intent if hasattr(context.latest_intent, "raw_utterance") else None
    latest_page = context.latest_page_understanding
    latest_product = latest_page.primary_product if latest_page is not None else None
    latest_verification = context.latest_verification

    warnings: list[str] = []
    if latest_verification is not None and latest_verification.decision != "MATCH":
        warnings.append(latest_verification.user_safe_summary)
    if context.latest_review_assessment is not None and context.latest_review_assessment.conflict_level in {
        ReviewConflictLevel.MEDIUM,
        ReviewConflictLevel.HIGH,
    }:
        warnings.append(context.latest_review_assessment.review_summary_spoken)
    if context.latest_low_confidence_status is not None and context.latest_low_confidence_status.active:
        if context.latest_low_confidence_status.reason:
            warnings.append(context.latest_low_confidence_status.reason)
    if (
        context.latest_clarification_request is not None
        and context.latest_clarification_request.status == ClarificationStatus.PENDING
        and context.latest_clarification_request.reason
    ):
        warnings.append(context.latest_clarification_request.reason)

    chosen_variant_parts = [
        _safe_text(latest_product.variant_text if latest_product is not None else None),
        _safe_text(context.latest_product_intent.color if context.latest_product_intent is not None else None),
        _safe_text(context.latest_product_intent.size_text if context.latest_product_intent is not None else None),
    ]
    chosen_variant = ", ".join(part for part in chosen_variant_parts if part) or None

    clarified_goal = None
    if (
        context.latest_clarification_request is not None
        and context.latest_clarification_request.clarified_response
    ):
        clarified_goal = context.latest_clarification_request.clarified_response
    elif context.latest_product_intent is not None:
        clarified_goal = context.latest_product_intent.raw_query

    return FinalSessionArtifact(
        original_goal=_safe_text(
            latest_intent.raw_utterance if latest_intent is not None else None
        ),
        clarified_goal=_safe_text(clarified_goal),
        chosen_product=_safe_text(
            context.latest_post_purchase_summary.order_item_title
            if context.latest_post_purchase_summary is not None
            else latest_product.title if latest_product is not None else None
        ),
        chosen_variant=chosen_variant,
        quantity_text=_safe_text(
            context.latest_product_intent.quantity_text if context.latest_product_intent is not None else None
        ),
        merchant=_safe_text(
            context.latest_trust_assessment.merchant if context.latest_trust_assessment is not None else None
        ),
        trust_status=(
            context.latest_trust_assessment.status.value
            if context.latest_trust_assessment is not None
            else None
        ),
        warnings=warnings,
        important_actions=_important_actions(logs),
        cart_snapshot=context.latest_cart_snapshot,
        checkpoint_history=_checkpoint_history(context),
        final_confirmation=context.latest_final_purchase_confirmation,
        post_purchase_summary=context.latest_post_purchase_summary,
        spoken_summary=context.latest_spoken_summary,
        completed_at=datetime.utcnow(),
    )


def build_final_self_diagnosis(
    *,
    context: SessionContextSnapshot,
    logs: list[AgentLogEntry],
) -> FinalSelfDiagnosis:
    unresolved_items: list[str] = []
    fallback_heavy_steps: list[str] = []
    confidence_warnings: list[str] = []

    if (
        context.latest_clarification_request is not None
        and context.latest_clarification_request.status == ClarificationStatus.PENDING
    ):
        unresolved_items.append("clarification_pending")
    if (
        context.latest_sensitive_checkpoint is not None
        and context.latest_sensitive_checkpoint.status.value == "PENDING"
    ):
        unresolved_items.append("sensitive_checkpoint_pending")
    if (
        context.latest_final_purchase_confirmation is not None
        and context.latest_final_purchase_confirmation.required
        and not context.latest_final_purchase_confirmation.confirmed
    ):
        unresolved_items.append("final_confirmation_pending")
    if context.latest_trust_assessment is not None and context.latest_trust_assessment.status.value != "TRUSTED":
        unresolved_items.append("merchant_trust_not_fully_verified")
    if context.latest_verification is not None and context.latest_verification.decision != "MATCH":
        unresolved_items.append(f"verification_{context.latest_verification.decision.value.lower()}")

    if context.latest_low_confidence_status is not None and context.latest_low_confidence_status.active:
        confidence_warnings.extend(context.latest_low_confidence_status.ambiguity_notes)
        if context.latest_low_confidence_status.reason:
            confidence_warnings.append(context.latest_low_confidence_status.reason)

    if context.latest_recovery_status is not None and context.latest_recovery_status.active:
        fallback_heavy_steps.append(
            context.latest_recovery_status.recovery_kind.value
            if context.latest_recovery_status.recovery_kind is not None
            else "recovery_active"
        )
        if context.latest_recovery_status.reason:
            confidence_warnings.append(context.latest_recovery_status.reason)

    for entry in logs:
        if entry.error_type:
            fallback_heavy_steps.append(entry.error_type)
        elif entry.step_type == AgentStepType.ERROR:
            fallback_heavy_steps.append(entry.state_after or "error_step")

    # Preserve order while removing duplicates.
    fallback_heavy_steps = list(dict.fromkeys(fallback_heavy_steps))
    confidence_warnings = list(dict.fromkeys([item for item in confidence_warnings if item]))

    ready_to_close = not unresolved_items and not confidence_warnings
    if ready_to_close:
        summary = "The session reached a clean closing state with no unresolved verification or consent blockers."
    else:
        summary = "The session can close, but unresolved ambiguity, fallback-heavy steps, or trust gaps remain recorded."

    return FinalSelfDiagnosis(
        ready_to_close=ready_to_close,
        unresolved_items=unresolved_items,
        fallback_heavy_steps=fallback_heavy_steps,
        confidence_warnings=confidence_warnings,
        summary=summary,
    )
