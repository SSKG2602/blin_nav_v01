from __future__ import annotations

from app.agent.decision_support import (
    derive_final_purchase_confirmation,
    derive_post_purchase_summary,
    derive_review_assessment,
    derive_trust_assessment,
)
from app.schemas.control_state import (
    CheckpointStatus,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.review_analysis import ReviewConflictLevel
from app.schemas.trust_verification import TrustStatus


def _assessment(decision: MultimodalDecision, confidence: float = 0.6) -> MultimodalAssessment:
    return MultimodalAssessment(
        decision=decision,
        confidence=confidence,
        confidence_band=ConfidenceBand.MEDIUM,
        needs_user_confirmation=decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION,
        needs_sensitive_checkpoint=decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT,
        should_halt_low_confidence=decision == MultimodalDecision.HALT_LOW_CONFIDENCE,
        ambiguity_notes=["test ambiguity"],
        trust_notes=["test trust"],
        review_notes=["test review"],
        reasoning_summary="test reasoning",
        recommended_next_step="test next",
        notes="test",
    )


def test_trust_assessment_trusted_known_merchant() -> None:
    assessment = derive_trust_assessment(
        observation={"observed_url": "https://www.amazon.in/dp/B0TESTSKU"},
        expected_merchant="amazon.in",
    )
    assert assessment.status == TrustStatus.TRUSTED
    assert assessment.https_present is True
    assert assessment.known_merchant_match is True


def test_trust_assessment_suspicious_lookalike_url() -> None:
    assessment = derive_trust_assessment(
        observation={"observed_url": "http://amaz0n-login.example.com/product"},
        expected_merchant="amazon.in",
    )
    assert assessment.status == TrustStatus.SUSPICIOUS
    assert assessment.lookalike_risk is True


def test_trust_assessment_unverified_unknown_url() -> None:
    assessment = derive_trust_assessment(
        observation={"observed_url": "https://store.example.org/item"},
        expected_merchant="amazon.in",
    )
    assert assessment.status == TrustStatus.UNVERIFIED
    assert assessment.domain == "store.example.org"


def test_review_assessment_levels_low_and_unknown() -> None:
    page_low = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        confidence=0.8,
        primary_product=ProductCandidate(
            rating_text="4.5 out of 5 stars",
            review_count_text="12,345 ratings",
        ),
    )
    low = derive_review_assessment(page=page_low)
    assert low.conflict_level == ReviewConflictLevel.LOW
    assert low.review_summary_spoken

    unknown = derive_review_assessment(page=None)
    assert unknown.conflict_level == ReviewConflictLevel.UNKNOWN


def test_review_assessment_medium_and_high_cases() -> None:
    medium_page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        confidence=0.7,
        primary_product=ProductCandidate(
            rating_text="4.0 out of 5 stars",
            review_count_text="25 ratings",
        ),
    )
    medium = derive_review_assessment(page=medium_page)
    assert medium.conflict_level in {ReviewConflictLevel.MEDIUM, ReviewConflictLevel.LOW}

    high_page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        confidence=0.7,
        primary_product=ProductCandidate(
            rating_text="3.0 out of 5 stars",
            review_count_text="222 ratings",
        ),
    )
    high = derive_review_assessment(page=high_page)
    assert high.conflict_level == ReviewConflictLevel.HIGH


def test_review_assessment_uses_review_snippets_for_conflict_and_spoken_summary() -> None:
    snippet_page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        confidence=0.82,
        primary_product=ProductCandidate(
            title="Pedigree Puppy Food 3kg",
            rating_text="4.2 out of 5 stars",
            review_count_text="240 ratings",
            review_snippets=[
                "Dogs love the taste and digestion improved quickly.",
                "Several buyers mention stomach upset and damaged packaging.",
                "The puppy pack size is convenient and easy to store.",
            ],
        ),
    )

    assessment = derive_review_assessment(page=snippet_page)

    assert assessment.conflict_level == ReviewConflictLevel.HIGH
    assert assessment.positive_signals
    assert assessment.negative_signals
    assert assessment.cited_snippets
    assert "positives:" in assessment.review_summary_spoken.lower()
    assert "negatives:" in assessment.review_summary_spoken.lower()


def test_final_purchase_confirmation_required_and_not_required() -> None:
    checkpoint = SensitiveCheckpointRequest(
        kind=SensitiveCheckpointKind.FINAL_PURCHASE_CONFIRMATION,
        status=CheckpointStatus.PENDING,
        reason="final confirmation required",
        prompt_to_user="Please confirm purchase.",
    )
    required = derive_final_purchase_confirmation(
        checkpoint=checkpoint,
        multimodal_assessment=_assessment(MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT),
        page=PageUnderstanding(page_type=PageType.CHECKOUT, confidence=0.8, checkout_ready=True),
        previous_confirmation=None,
    )
    assert required.required is True
    assert required.confirmed is False

    not_required = derive_final_purchase_confirmation(
        checkpoint=None,
        multimodal_assessment=_assessment(MultimodalDecision.PROCEED),
        page=PageUnderstanding(page_type=PageType.PRODUCT_DETAIL, confidence=0.8),
        previous_confirmation=None,
    )
    assert not_required.required is False


def test_post_purchase_summary_detected_and_fallback() -> None:
    detected = derive_post_purchase_summary(
        page=PageUnderstanding(
            page_type=PageType.CHECKOUT,
            page_title="Thank you, your order has been placed",
            confidence=0.85,
            primary_product=ProductCandidate(title="Dog Food 3kg", price_text="₹799"),
        ),
        observation={"observed_url": "https://www.amazon.in/order-confirmation"},
    )
    assert "order appears placed" in detected.spoken_summary.lower()
    assert detected.order_item_title == "Dog Food 3kg"

    fallback = derive_post_purchase_summary(
        page=PageUnderstanding(page_type=PageType.PRODUCT_DETAIL, page_title="Product page", confidence=0.8),
        observation={},
    )
    assert "not visible yet" in fallback.spoken_summary.lower()
