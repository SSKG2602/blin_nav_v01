from __future__ import annotations

from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.page_understanding import PageType, PageUnderstanding
from app.schemas.product_verification import ProductIntentSpec, ProductVerificationResult, VerificationDecision


def _confidence_band(confidence: float) -> ConfidenceBand:
    if confidence >= 0.75:
        return ConfidenceBand.HIGH
    if confidence >= 0.45:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def _recommended_next_step(decision: MultimodalDecision) -> str:
    if decision == MultimodalDecision.PROCEED:
        return "continue_agent_flow"
    if decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION:
        return "ask_user_confirmation"
    if decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT:
        return "request_sensitive_checkpoint"
    return "halt_and_clarify"


def _decision_flags(decision: MultimodalDecision) -> tuple[bool, bool, bool]:
    return (
        decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
        decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
        decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
    )


def build_fallback_multimodal_assessment(
    *,
    intent: ProductIntentSpec | None,
    page: PageUnderstanding | None,
    verification: ProductVerificationResult | None,
    spoken_summary: str | None = None,
) -> MultimodalAssessment:
    decision = MultimodalDecision.REQUIRE_USER_CONFIRMATION
    confidence = 0.45
    ambiguity_notes: list[str] = []
    trust_notes: list[str] = []
    review_notes: list[str] = []

    if intent is None:
        ambiguity_notes.append("Product intent is missing.")
        confidence -= 0.08
    else:
        trust_notes.append("Product intent is available.")

    if page is None:
        ambiguity_notes.append("Page understanding is unavailable.")
        confidence -= 0.20
    else:
        trust_notes.append(f"Page type detected as {page.page_type.value}.")
        confidence += min(0.18, page.confidence * 0.2)

    if verification is None:
        review_notes.append("Verification result not available.")
        confidence -= 0.08
    else:
        review_notes.append(f"Verification decision: {verification.decision.value}.")
        if verification.decision == VerificationDecision.MATCH:
            confidence += 0.30
            trust_notes.append("Verification strongly matches requested product.")
            if page is not None and page.page_type in {PageType.PRODUCT_DETAIL, PageType.CART}:
                decision = MultimodalDecision.PROCEED
        elif verification.decision in {
            VerificationDecision.PARTIAL_MATCH,
            VerificationDecision.AMBIGUOUS,
        }:
            confidence -= 0.04
            decision = MultimodalDecision.REQUIRE_USER_CONFIRMATION
            ambiguity_notes.append("Verification indicates partial or ambiguous match.")
        elif verification.decision in {
            VerificationDecision.MISMATCH,
            VerificationDecision.INSUFFICIENT_EVIDENCE,
        }:
            confidence -= 0.28
            decision = MultimodalDecision.HALT_LOW_CONFIDENCE
            ambiguity_notes.append("Verification is weak or mismatched.")

    checkout_like = False
    if page is not None:
        checkout_like = bool(
            page.page_type == PageType.CHECKOUT
            or page.checkout_ready is True
        )
    if checkout_like and decision != MultimodalDecision.HALT_LOW_CONFIDENCE:
        decision = MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT
        trust_notes.append("Checkout-like context detected; sensitive checkpoint required.")
        confidence = max(confidence, 0.58)

    if page is None and verification is None:
        decision = MultimodalDecision.HALT_LOW_CONFIDENCE
        ambiguity_notes.append("Both page and verification evidence are unavailable.")

    confidence = max(0.05, min(0.95, confidence))
    confidence_band = _confidence_band(confidence)
    needs_user_confirmation, needs_sensitive_checkpoint, should_halt_low_confidence = _decision_flags(decision)

    if decision == MultimodalDecision.PROCEED:
        reasoning_summary = "Evidence is sufficiently aligned to proceed carefully."
    elif decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION:
        reasoning_summary = "Evidence is partially aligned; user confirmation is required."
    elif decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT:
        reasoning_summary = "Sensitive action context detected; explicit checkpoint is required."
    else:
        reasoning_summary = "Evidence is weak or conflicting; halting for safety."

    if spoken_summary:
        review_notes.append("Spoken summary was considered in decision support.")

    return MultimodalAssessment(
        decision=decision,
        confidence=confidence,
        confidence_band=confidence_band,
        needs_user_confirmation=needs_user_confirmation,
        needs_sensitive_checkpoint=needs_sensitive_checkpoint,
        should_halt_low_confidence=should_halt_low_confidence,
        ambiguity_notes=ambiguity_notes,
        trust_notes=trust_notes,
        review_notes=review_notes,
        reasoning_summary=reasoning_summary,
        recommended_next_step=_recommended_next_step(decision),
        notes="Deterministic fallback multimodal assessment.",
    )
