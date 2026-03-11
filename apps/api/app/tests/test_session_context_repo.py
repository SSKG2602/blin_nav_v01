from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import AgentLogORM, SessionContextORM, SessionORM
from app.repositories.session_context_repo import (
    get_or_create_session_context,
    get_session_context,
    update_session_context,
)
from app.repositories.session_repo import create_session
from app.schemas.control_state import (
    CheckpointStatus,
    LowConfidenceStatus,
    RecoveryKind,
    RecoveryStatus,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.intent import InterpretedUserIntent, ShoppingAction
from app.schemas.multimodal_assessment import (
    ConfidenceBand,
    MultimodalAssessment,
    MultimodalDecision,
)
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.purchase_support import FinalPurchaseConfirmation, PostPurchaseSummary
from app.schemas.review_analysis import ReviewAssessment, ReviewConflictLevel
from app.schemas.product_verification import (
    ProductIntentSpec,
    ProductVerificationResult,
    VerificationDecision,
)
from app.schemas.session import SessionCreate
from app.schemas.trust_verification import TrustAssessment, TrustStatus


@pytest.fixture
def db_session():
    assert SessionORM is not None
    assert AgentLogORM is not None
    assert SessionContextORM is not None

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    with testing_session_local() as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def test_session_context_create_read_update(db_session) -> None:
    created = create_session(db_session, SessionCreate())
    session_id = created.session_id

    empty = get_session_context(db_session, session_id)
    assert empty is None

    initial = get_or_create_session_context(db_session, session_id)
    assert initial.session_id == session_id
    assert initial.latest_intent is None

    updated = update_session_context(
        db_session,
        session_id,
        latest_intent=InterpretedUserIntent(
            raw_utterance="find dog food",
            action=ShoppingAction.SEARCH_PRODUCT,
            merchant="demo.nopcommerce.com",
            confidence=0.7,
            requires_clarification=False,
            spoken_confirmation="Searching now.",
        ),
        latest_product_intent=ProductIntentSpec(raw_query="dog food", product_name="dog food"),
        latest_page_understanding=PageUnderstanding(
            page_type=PageType.PRODUCT_DETAIL,
            page_title="Dog Food",
            primary_product=ProductCandidate(title="Dog Food 3kg", price_text="₹799"),
            confidence=0.7,
        ),
        latest_verification=ProductVerificationResult(
            decision=VerificationDecision.PARTIAL_MATCH,
            matched_fields=["product_name"],
            mismatched_fields=[],
            missing_fields=["size_text"],
            confidence=0.55,
            user_safe_summary="Possible match, needs confirmation.",
        ),
        latest_multimodal_assessment=MultimodalAssessment(
            decision=MultimodalDecision.REQUIRE_USER_CONFIRMATION,
            confidence=0.58,
            confidence_band=ConfidenceBand.MEDIUM,
            needs_user_confirmation=True,
            needs_sensitive_checkpoint=False,
            should_halt_low_confidence=False,
            ambiguity_notes=["Variant is not fully clear."],
            trust_notes=["Primary product details are available."],
            review_notes=["Require explicit user verification."],
            reasoning_summary="Current evidence suggests confirmation is safer than auto-proceed.",
            recommended_next_step="ask_user_confirmation",
            notes="Repository test payload.",
        ),
        latest_sensitive_checkpoint=SensitiveCheckpointRequest(
            kind=SensitiveCheckpointKind.PAYMENT_CONFIRMATION,
            status=CheckpointStatus.PENDING,
            reason="Sensitive confirmation needed before checkout.",
            prompt_to_user="Please confirm payment step.",
        ),
        latest_low_confidence_status=LowConfidenceStatus(
            active=False,
            reason=None,
            confidence=0.58,
            ambiguity_notes=[],
            trust_notes=["Evidence partially aligned."],
            review_notes=[],
            recommended_next_step="ask_user_confirmation",
        ),
        latest_recovery_status=RecoveryStatus(
            active=False,
            recovery_kind=None,
            reason=None,
            last_attempt_summary=None,
            last_updated_at=None,
        ),
        latest_trust_assessment=TrustAssessment(
            status=TrustStatus.TRUSTED,
            merchant="demo.nopcommerce.com",
            domain="demo.nopcommerce.com",
            https_present=True,
            lookalike_risk=False,
            known_merchant_match=True,
            reasoning_summary="Trusted merchant and HTTPS checks passed.",
        ),
        latest_review_assessment=ReviewAssessment(
            conflict_level=ReviewConflictLevel.LOW,
            rating_text="4.4 out of 5 stars",
            review_count_text="12,345 ratings",
            review_summary_spoken="Review signals look generally consistent.",
            conflict_notes=["High review volume with strong rating."],
            confidence=0.75,
        ),
        latest_final_purchase_confirmation=FinalPurchaseConfirmation(
            required=True,
            confirmed=False,
            prompt_to_user="Please confirm final purchase.",
            confirmation_phrase_expected="confirm purchase",
            notes="Pending explicit confirmation.",
        ),
        latest_post_purchase_summary=PostPurchaseSummary(
            order_item_title=None,
            order_price_text=None,
            delivery_window_text=None,
            orders_location_hint="Open Orders page after confirmation.",
            spoken_summary="Post-purchase confirmation is not visible yet.",
            notes="Weak post-purchase evidence.",
        ),
        latest_spoken_summary="I found a possible match.",
    )

    assert updated.session_id == session_id
    assert updated.latest_product_intent is not None
    assert updated.latest_page_understanding is not None
    assert updated.latest_verification is not None
    assert updated.latest_multimodal_assessment is not None
    assert updated.latest_sensitive_checkpoint is not None
    assert updated.latest_low_confidence_status is not None
    assert updated.latest_recovery_status is not None
    assert updated.latest_trust_assessment is not None
    assert updated.latest_review_assessment is not None
    assert updated.latest_final_purchase_confirmation is not None
    assert updated.latest_post_purchase_summary is not None
    assert updated.latest_spoken_summary == "I found a possible match."

    loaded = get_session_context(db_session, session_id)
    assert loaded is not None
    assert loaded.session_id == UUID(str(session_id))
    assert loaded.latest_page_understanding is not None
    assert loaded.latest_page_understanding.page_type == PageType.PRODUCT_DETAIL
    assert loaded.latest_multimodal_assessment is not None
    assert loaded.latest_multimodal_assessment.decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION
    assert loaded.latest_sensitive_checkpoint is not None
    assert loaded.latest_sensitive_checkpoint.status == CheckpointStatus.PENDING
    assert loaded.latest_low_confidence_status is not None
    assert loaded.latest_low_confidence_status.active is False
    assert loaded.latest_recovery_status is not None
    assert loaded.latest_recovery_status.recovery_kind in {None, RecoveryKind.NAVIGATION_RECOVERY}
    assert loaded.latest_trust_assessment is not None
    assert loaded.latest_trust_assessment.status == TrustStatus.TRUSTED
    assert loaded.latest_review_assessment is not None
    assert loaded.latest_review_assessment.conflict_level == ReviewConflictLevel.LOW
    assert loaded.latest_final_purchase_confirmation is not None
    assert loaded.latest_final_purchase_confirmation.required is True
    assert loaded.latest_post_purchase_summary is not None
