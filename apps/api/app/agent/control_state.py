from __future__ import annotations

from datetime import datetime

from app.schemas.control_state import (
    CheckpointStatus,
    LowConfidenceStatus,
    RecoveryKind,
    RecoveryStatus,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.multimodal_assessment import MultimodalAssessment, MultimodalDecision
from app.schemas.page_understanding import PageType, PageUnderstanding
from app.schemas.product_verification import ProductVerificationResult


def _infer_checkpoint_kind(
    page: PageUnderstanding | None,
    verification: ProductVerificationResult | None,
) -> SensitiveCheckpointKind:
    if page is None:
        return SensitiveCheckpointKind.UNKNOWN

    title = (page.page_title or "").lower()
    notes = (page.notes or "").lower()
    combined = f"{title} {notes}"

    if "otp" in combined:
        return SensitiveCheckpointKind.OTP
    if "captcha" in combined:
        return SensitiveCheckpointKind.CAPTCHA
    if "address" in combined:
        return SensitiveCheckpointKind.ADDRESS_CONFIRMATION
    if "payment" in combined or page.page_type == PageType.CHECKOUT:
        if verification is not None:
            return SensitiveCheckpointKind.FINAL_PURCHASE_CONFIRMATION
        return SensitiveCheckpointKind.PAYMENT_CONFIRMATION

    return SensitiveCheckpointKind.UNKNOWN


def _checkpoint_prompt(kind: SensitiveCheckpointKind) -> str:
    if kind == SensitiveCheckpointKind.OTP:
        return "An OTP verification step is detected. Please confirm before continuing."
    if kind == SensitiveCheckpointKind.CAPTCHA:
        return "A CAPTCHA challenge is detected. Please assist with manual verification."
    if kind == SensitiveCheckpointKind.PAYMENT_CONFIRMATION:
        return "Payment confirmation is required. Please confirm if I should continue."
    if kind == SensitiveCheckpointKind.ADDRESS_CONFIRMATION:
        return "Address confirmation is required. Please verify the selected address."
    if kind == SensitiveCheckpointKind.FINAL_PURCHASE_CONFIRMATION:
        return "Final purchase confirmation is required. Please approve before proceeding."
    return "A sensitive checkpoint is detected. Please confirm the next action."


def derive_sensitive_checkpoint(
    *,
    multimodal_assessment: MultimodalAssessment | None,
    page: PageUnderstanding | None,
    verification: ProductVerificationResult | None,
    previous_checkpoint: SensitiveCheckpointRequest | None = None,
) -> SensitiveCheckpointRequest | None:
    if multimodal_assessment is None:
        return None

    if not (
        multimodal_assessment.decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT
        or multimodal_assessment.needs_sensitive_checkpoint
    ):
        return None

    kind = _infer_checkpoint_kind(page, verification)
    if (
        previous_checkpoint is not None
        and previous_checkpoint.kind == kind
        and previous_checkpoint.status != CheckpointStatus.PENDING
    ):
        return previous_checkpoint

    return SensitiveCheckpointRequest(
        kind=kind,
        status=CheckpointStatus.PENDING,
        reason=multimodal_assessment.reasoning_summary,
        prompt_to_user=_checkpoint_prompt(kind),
        created_at=datetime.utcnow(),
        resolved_at=None,
        resolution_notes=None,
    )


def derive_low_confidence_status(
    *,
    multimodal_assessment: MultimodalAssessment | None,
) -> LowConfidenceStatus:
    if multimodal_assessment is None:
        return LowConfidenceStatus(
            active=False,
            reason=None,
            confidence=None,
            ambiguity_notes=[],
            trust_notes=[],
            review_notes=[],
            recommended_next_step=None,
        )

    active = bool(
        multimodal_assessment.decision == MultimodalDecision.HALT_LOW_CONFIDENCE
        or multimodal_assessment.should_halt_low_confidence
    )
    if not active:
        return LowConfidenceStatus(
            active=False,
            reason=None,
            confidence=multimodal_assessment.confidence,
            ambiguity_notes=[],
            trust_notes=[],
            review_notes=[],
            recommended_next_step=multimodal_assessment.recommended_next_step,
        )

    return LowConfidenceStatus(
        active=True,
        reason=multimodal_assessment.reasoning_summary,
        confidence=multimodal_assessment.confidence,
        ambiguity_notes=list(multimodal_assessment.ambiguity_notes),
        trust_notes=list(multimodal_assessment.trust_notes),
        review_notes=list(multimodal_assessment.review_notes),
        recommended_next_step=multimodal_assessment.recommended_next_step,
    )


def derive_recovery_status(
    *,
    multimodal_assessment: MultimodalAssessment | None,
    page: PageUnderstanding | None,
    low_confidence_status: LowConfidenceStatus | None,
) -> RecoveryStatus:
    now = datetime.utcnow()
    page_notes = (page.notes or "").lower() if page is not None else ""

    if "modal" in page_notes or "popup" in page_notes or "captcha" in page_notes:
        return RecoveryStatus(
            active=True,
            recovery_kind=RecoveryKind.MODAL_INTERRUPTION,
            reason="Page indicates modal interruption signals.",
            last_attempt_summary="Attempt modal dismissal and re-sync page understanding.",
            last_updated_at=now,
        )

    if page is not None and page.page_type == PageType.UNKNOWN and page.confidence < 0.35:
        return RecoveryStatus(
            active=True,
            recovery_kind=RecoveryKind.PAGE_DESYNC,
            reason="Page understanding confidence is too low.",
            last_attempt_summary="Run navigation recovery to a known stable page.",
            last_updated_at=now,
        )

    if (
        low_confidence_status is not None
        and low_confidence_status.active
        and page is not None
        and (page.page_type == PageType.CHECKOUT or page.checkout_ready is True)
    ):
        return RecoveryStatus(
            active=True,
            recovery_kind=RecoveryKind.CHECKOUT_BLOCKED,
            reason=low_confidence_status.reason or "Low confidence while entering checkout.",
            last_attempt_summary="Back out to cart/home and request explicit confirmation.",
            last_updated_at=now,
        )

    if (
        low_confidence_status is not None
        and low_confidence_status.active
        and multimodal_assessment is not None
    ):
        return RecoveryStatus(
            active=True,
            recovery_kind=RecoveryKind.NAVIGATION_RECOVERY,
            reason=multimodal_assessment.reasoning_summary,
            last_attempt_summary=multimodal_assessment.recommended_next_step,
            last_updated_at=now,
        )

    return RecoveryStatus(
        active=False,
        recovery_kind=None,
        reason=None,
        last_attempt_summary=None,
        last_updated_at=None,
    )
