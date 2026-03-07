from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

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
from app.schemas.trust_verification import TrustAssessment


class SessionContextSnapshot(BaseModel):
    session_id: UUID
    latest_intent: InterpretedUserIntent | dict[str, Any] | None = None
    latest_product_intent: ProductIntentSpec | None = None
    latest_page_understanding: PageUnderstanding | None = None
    latest_verification: ProductVerificationResult | None = None
    latest_multimodal_assessment: MultimodalAssessment | None = None
    latest_sensitive_checkpoint: SensitiveCheckpointRequest | None = None
    latest_low_confidence_status: LowConfidenceStatus | None = None
    latest_recovery_status: RecoveryStatus | None = None
    latest_trust_assessment: TrustAssessment | None = None
    latest_review_assessment: ReviewAssessment | None = None
    latest_final_purchase_confirmation: FinalPurchaseConfirmation | None = None
    latest_post_purchase_summary: PostPurchaseSummary | None = None
    latest_spoken_summary: str | None = None
    updated_at: datetime | None = None
