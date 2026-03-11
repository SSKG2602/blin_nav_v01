from __future__ import annotations

from app.agent.control_state import (
    derive_low_confidence_status,
    derive_recovery_status,
    derive_sensitive_checkpoint,
)
from app.agent.state import AgentState
from app.schemas.control_state import CheckpointStatus, RecoveryKind, SensitiveCheckpointKind
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.page_understanding import PageType, PageUnderstanding
from app.schemas.product_verification import ProductVerificationResult, VerificationDecision


def _assessment(decision: MultimodalDecision, confidence: float = 0.6) -> MultimodalAssessment:
    return MultimodalAssessment(
        decision=decision,
        confidence=confidence,
        confidence_band=ConfidenceBand.MEDIUM if confidence >= 0.45 else ConfidenceBand.LOW,
        needs_user_confirmation=decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
        needs_sensitive_checkpoint=decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
        should_halt_low_confidence=decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
        ambiguity_notes=["a"],
        trust_notes=["t"],
        review_notes=["r"],
        reasoning_summary=f"Decision: {decision.value}",
        recommended_next_step="next_step",
        notes="test",
    )


def test_derive_sensitive_checkpoint_from_multimodal_checkpoint_decision() -> None:
    page = PageUnderstanding(page_type=PageType.CHECKOUT, confidence=0.8, checkout_ready=True)
    verification = ProductVerificationResult(
        decision=VerificationDecision.MATCH,
        matched_fields=["product_name"],
        mismatched_fields=[],
        missing_fields=[],
        confidence=0.8,
        user_safe_summary="match",
    )
    checkpoint = derive_sensitive_checkpoint(
        multimodal_assessment=_assessment(MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT),
        page=page,
        verification=verification,
    )

    assert checkpoint is not None
    assert checkpoint.status == CheckpointStatus.PENDING
    assert checkpoint.kind in {
        SensitiveCheckpointKind.FINAL_PURCHASE_CONFIRMATION,
        SensitiveCheckpointKind.PAYMENT_CONFIRMATION,
    }
    assert checkpoint.prompt_to_user


def test_derive_low_confidence_status_for_halt_case() -> None:
    status = derive_low_confidence_status(
        multimodal_assessment=_assessment(MultimodalDecision.HALT_LOW_CONFIDENCE, confidence=0.2),
    )
    assert status.active is True
    assert status.reason is not None
    assert status.confidence is not None


def test_derive_recovery_status_for_desync_case() -> None:
    page = PageUnderstanding(page_type=PageType.UNKNOWN, confidence=0.2, notes="page desync signal")
    low_conf = derive_low_confidence_status(
        multimodal_assessment=_assessment(MultimodalDecision.HALT_LOW_CONFIDENCE, confidence=0.2),
    )

    recovery = derive_recovery_status(
        current_state=AgentState.SEARCHING_PRODUCTS,
        multimodal_assessment=_assessment(MultimodalDecision.HALT_LOW_CONFIDENCE, confidence=0.2),
        page=page,
        low_confidence_status=low_conf,
    )
    assert recovery.active is True
    assert recovery.recovery_kind in {RecoveryKind.PAGE_DESYNC, RecoveryKind.NAVIGATION_RECOVERY}
    assert recovery.last_updated_at is not None


def test_derive_recovery_status_for_expected_state_mismatch() -> None:
    page = PageUnderstanding(
        page_type=PageType.CART,
        confidence=0.8,
        notes="weak_page_evidence cart_anchor_present",
    )
    recovery = derive_recovery_status(
        current_state=AgentState.SEARCHING_PRODUCTS,
        multimodal_assessment=_assessment(MultimodalDecision.PROCEED, confidence=0.75),
        page=page,
        low_confidence_status=derive_low_confidence_status(
            multimodal_assessment=_assessment(MultimodalDecision.PROCEED, confidence=0.75),
        ),
    )

    assert recovery.active is True
    assert recovery.recovery_kind == RecoveryKind.PAGE_DESYNC
    assert recovery.expected_state == AgentState.SEARCHING_PRODUCTS.value
    assert recovery.observed_page_type == PageType.CART.value
    assert recovery.recovery_outcome == "pending_reconciliation"


def test_derive_recovery_status_for_selector_degradation() -> None:
    page = PageUnderstanding(
        page_type=PageType.SEARCH_RESULTS,
        confidence=0.62,
        detected_page_hints=["search_results", "selector_degradation"],
        notes="selector degradation detected while stabilizing results",
    )

    recovery = derive_recovery_status(
        current_state=AgentState.SEARCHING_PRODUCTS,
        multimodal_assessment=_assessment(MultimodalDecision.PROCEED, confidence=0.7),
        page=page,
        low_confidence_status=derive_low_confidence_status(
            multimodal_assessment=_assessment(MultimodalDecision.PROCEED, confidence=0.7),
        ),
    )

    assert recovery.active is True
    assert recovery.recovery_kind == RecoveryKind.PAGE_DESYNC
    assert recovery.recovery_outcome == "selector_degradation"


def test_derive_sensitive_checkpoint_from_explicit_captcha_signal() -> None:
    page = PageUnderstanding(
        page_type=PageType.CHECKOUT,
        page_title="Checkout verification",
        confidence=0.82,
        notes="captcha_visible checkout_anchor_present",
    )

    checkpoint = derive_sensitive_checkpoint(
        multimodal_assessment=None,
        page=page,
        verification=None,
    )

    assert checkpoint is not None
    assert checkpoint.kind == SensitiveCheckpointKind.CAPTCHA
    assert checkpoint.status == CheckpointStatus.PENDING
    assert "manual verification" in checkpoint.prompt_to_user.lower()


def test_derive_sensitive_checkpoint_from_explicit_otp_signal() -> None:
    page = PageUnderstanding(
        page_type=PageType.CHECKOUT,
        page_title="Checkout verification code",
        confidence=0.81,
        notes="otp_required payment_auth_required",
    )

    checkpoint = derive_sensitive_checkpoint(
        multimodal_assessment=None,
        page=page,
        verification=None,
    )

    assert checkpoint is not None
    assert checkpoint.kind == SensitiveCheckpointKind.OTP
    assert checkpoint.status == CheckpointStatus.PENDING
    assert "otp verification" in checkpoint.prompt_to_user.lower()


def test_benign_case_returns_inactive_controls() -> None:
    page = PageUnderstanding(page_type=PageType.PRODUCT_DETAIL, confidence=0.85)
    assessment = _assessment(MultimodalDecision.PROCEED, confidence=0.85)

    checkpoint = derive_sensitive_checkpoint(
        multimodal_assessment=assessment,
        page=page,
        verification=None,
    )
    low_conf = derive_low_confidence_status(multimodal_assessment=assessment)
    recovery = derive_recovery_status(
        current_state=AgentState.VIEWING_PRODUCT_DETAIL,
        multimodal_assessment=assessment,
        page=page,
        low_confidence_status=low_conf,
    )

    assert checkpoint is None
    assert low_conf.active is False
    assert recovery.active is False
