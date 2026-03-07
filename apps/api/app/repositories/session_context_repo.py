from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.session import SessionContextORM, SessionORM
from app.schemas.control_state import (
    LowConfidenceStatus,
    RecoveryStatus,
    SensitiveCheckpointRequest,
)
from app.schemas.intent import InterpretedUserIntent
from app.schemas.multimodal_assessment import MultimodalAssessment
from app.schemas.page_understanding import PageUnderstanding
from app.schemas.purchase_support import FinalPurchaseConfirmation, PostPurchaseSummary
from app.schemas.review_analysis import ReviewAssessment
from app.schemas.product_verification import ProductIntentSpec, ProductVerificationResult
from app.schemas.session_context import SessionContextSnapshot
from app.schemas.trust_verification import TrustAssessment

_UNSET = object()


def _coerce_interpreted_intent(value: Any) -> InterpretedUserIntent | dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, InterpretedUserIntent):
        return value
    if isinstance(value, dict):
        try:
            return InterpretedUserIntent.model_validate(value)
        except ValidationError:
            return value
    return None


def _coerce_product_intent(value: Any) -> ProductIntentSpec | None:
    if value is None:
        return None
    if isinstance(value, ProductIntentSpec):
        return value
    if isinstance(value, dict):
        try:
            return ProductIntentSpec.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_page_understanding(value: Any) -> PageUnderstanding | None:
    if value is None:
        return None
    if isinstance(value, PageUnderstanding):
        return value
    if isinstance(value, dict):
        try:
            return PageUnderstanding.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_verification(value: Any) -> ProductVerificationResult | None:
    if value is None:
        return None
    if isinstance(value, ProductVerificationResult):
        return value
    if isinstance(value, dict):
        try:
            return ProductVerificationResult.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_multimodal_assessment(value: Any) -> MultimodalAssessment | None:
    if value is None:
        return None
    if isinstance(value, MultimodalAssessment):
        return value
    if isinstance(value, dict):
        try:
            return MultimodalAssessment.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_sensitive_checkpoint(value: Any) -> SensitiveCheckpointRequest | None:
    if value is None:
        return None
    if isinstance(value, SensitiveCheckpointRequest):
        return value
    if isinstance(value, dict):
        try:
            return SensitiveCheckpointRequest.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_low_confidence_status(value: Any) -> LowConfidenceStatus | None:
    if value is None:
        return None
    if isinstance(value, LowConfidenceStatus):
        return value
    if isinstance(value, dict):
        try:
            return LowConfidenceStatus.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_recovery_status(value: Any) -> RecoveryStatus | None:
    if value is None:
        return None
    if isinstance(value, RecoveryStatus):
        return value
    if isinstance(value, dict):
        try:
            return RecoveryStatus.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_trust_assessment(value: Any) -> TrustAssessment | None:
    if value is None:
        return None
    if isinstance(value, TrustAssessment):
        return value
    if isinstance(value, dict):
        try:
            return TrustAssessment.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_review_assessment(value: Any) -> ReviewAssessment | None:
    if value is None:
        return None
    if isinstance(value, ReviewAssessment):
        return value
    if isinstance(value, dict):
        try:
            return ReviewAssessment.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_final_purchase_confirmation(value: Any) -> FinalPurchaseConfirmation | None:
    if value is None:
        return None
    if isinstance(value, FinalPurchaseConfirmation):
        return value
    if isinstance(value, dict):
        try:
            return FinalPurchaseConfirmation.model_validate(value)
        except ValidationError:
            return None
    return None


def _coerce_post_purchase_summary(value: Any) -> PostPurchaseSummary | None:
    if value is None:
        return None
    if isinstance(value, PostPurchaseSummary):
        return value
    if isinstance(value, dict):
        try:
            return PostPurchaseSummary.model_validate(value)
        except ValidationError:
            return None
    return None


def _intent_to_json(value: InterpretedUserIntent | dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, InterpretedUserIntent):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return None


def _model_to_json(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        payload = dump(mode="json")
        return payload if isinstance(payload, dict) else None
    if isinstance(value, dict):
        return value
    return None


def _to_snapshot(row: SessionContextORM) -> SessionContextSnapshot:
    return SessionContextSnapshot(
        session_id=UUID(row.session_id),
        latest_intent=_coerce_interpreted_intent(row.latest_intent_json),
        latest_product_intent=_coerce_product_intent(row.latest_product_intent_json),
        latest_page_understanding=_coerce_page_understanding(row.latest_page_understanding_json),
        latest_verification=_coerce_verification(row.latest_verification_json),
        latest_multimodal_assessment=_coerce_multimodal_assessment(
            row.latest_multimodal_assessment_json
        ),
        latest_sensitive_checkpoint=_coerce_sensitive_checkpoint(
            row.latest_sensitive_checkpoint_json
        ),
        latest_low_confidence_status=_coerce_low_confidence_status(
            row.latest_low_confidence_status_json
        ),
        latest_recovery_status=_coerce_recovery_status(
            row.latest_recovery_status_json
        ),
        latest_trust_assessment=_coerce_trust_assessment(
            row.latest_trust_assessment_json
        ),
        latest_review_assessment=_coerce_review_assessment(
            row.latest_review_assessment_json
        ),
        latest_final_purchase_confirmation=_coerce_final_purchase_confirmation(
            row.latest_final_purchase_confirmation_json
        ),
        latest_post_purchase_summary=_coerce_post_purchase_summary(
            row.latest_post_purchase_summary_json
        ),
        latest_spoken_summary=row.latest_spoken_summary,
        updated_at=row.updated_at,
    )


def _ensure_session_exists(db: Session, session_id: UUID) -> None:
    session_row = db.query(SessionORM).filter(SessionORM.id == str(session_id)).first()
    if session_row is None:
        raise ValueError("Session does not exist")


def get_session_context(db: Session, session_id: UUID) -> SessionContextSnapshot | None:
    row = db.query(SessionContextORM).filter(SessionContextORM.session_id == str(session_id)).first()
    if row is None:
        return None
    return _to_snapshot(row)


def get_or_create_session_context(db: Session, session_id: UUID) -> SessionContextSnapshot:
    _ensure_session_exists(db, session_id)
    row = db.query(SessionContextORM).filter(SessionContextORM.session_id == str(session_id)).first()
    if row is None:
        row = SessionContextORM(
            session_id=str(session_id),
            updated_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return _to_snapshot(row)


def update_session_context(
    db: Session,
    session_id: UUID,
    *,
    latest_intent: InterpretedUserIntent | dict[str, Any] | None | object = _UNSET,
    latest_product_intent: ProductIntentSpec | None | object = _UNSET,
    latest_page_understanding: PageUnderstanding | None | object = _UNSET,
    latest_verification: ProductVerificationResult | None | object = _UNSET,
    latest_multimodal_assessment: MultimodalAssessment | None | object = _UNSET,
    latest_sensitive_checkpoint: SensitiveCheckpointRequest | None | object = _UNSET,
    latest_low_confidence_status: LowConfidenceStatus | None | object = _UNSET,
    latest_recovery_status: RecoveryStatus | None | object = _UNSET,
    latest_trust_assessment: TrustAssessment | None | object = _UNSET,
    latest_review_assessment: ReviewAssessment | None | object = _UNSET,
    latest_final_purchase_confirmation: FinalPurchaseConfirmation | None | object = _UNSET,
    latest_post_purchase_summary: PostPurchaseSummary | None | object = _UNSET,
    latest_spoken_summary: str | None | object = _UNSET,
) -> SessionContextSnapshot:
    _ensure_session_exists(db, session_id)
    row = db.query(SessionContextORM).filter(SessionContextORM.session_id == str(session_id)).first()
    if row is None:
        row = SessionContextORM(session_id=str(session_id))
        db.add(row)

    if latest_intent is not _UNSET:
        row.latest_intent_json = _intent_to_json(latest_intent if latest_intent is not _UNSET else None)
    if latest_product_intent is not _UNSET:
        row.latest_product_intent_json = _model_to_json(
            latest_product_intent if latest_product_intent is not _UNSET else None
        )
    if latest_page_understanding is not _UNSET:
        row.latest_page_understanding_json = _model_to_json(
            latest_page_understanding if latest_page_understanding is not _UNSET else None
        )
    if latest_verification is not _UNSET:
        row.latest_verification_json = _model_to_json(
            latest_verification if latest_verification is not _UNSET else None
        )
    if latest_multimodal_assessment is not _UNSET:
        row.latest_multimodal_assessment_json = _model_to_json(
            latest_multimodal_assessment
            if latest_multimodal_assessment is not _UNSET
            else None
        )
    if latest_sensitive_checkpoint is not _UNSET:
        row.latest_sensitive_checkpoint_json = _model_to_json(
            latest_sensitive_checkpoint
            if latest_sensitive_checkpoint is not _UNSET
            else None
        )
    if latest_low_confidence_status is not _UNSET:
        row.latest_low_confidence_status_json = _model_to_json(
            latest_low_confidence_status
            if latest_low_confidence_status is not _UNSET
            else None
        )
    if latest_recovery_status is not _UNSET:
        row.latest_recovery_status_json = _model_to_json(
            latest_recovery_status
            if latest_recovery_status is not _UNSET
            else None
        )
    if latest_trust_assessment is not _UNSET:
        row.latest_trust_assessment_json = _model_to_json(
            latest_trust_assessment
            if latest_trust_assessment is not _UNSET
            else None
        )
    if latest_review_assessment is not _UNSET:
        row.latest_review_assessment_json = _model_to_json(
            latest_review_assessment
            if latest_review_assessment is not _UNSET
            else None
        )
    if latest_final_purchase_confirmation is not _UNSET:
        row.latest_final_purchase_confirmation_json = _model_to_json(
            latest_final_purchase_confirmation
            if latest_final_purchase_confirmation is not _UNSET
            else None
        )
    if latest_post_purchase_summary is not _UNSET:
        row.latest_post_purchase_summary_json = _model_to_json(
            latest_post_purchase_summary
            if latest_post_purchase_summary is not _UNSET
            else None
        )
    if latest_spoken_summary is not _UNSET:
        row.latest_spoken_summary = (
            latest_spoken_summary if isinstance(latest_spoken_summary, str) or latest_spoken_summary is None else None
        )

    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_snapshot(row)
