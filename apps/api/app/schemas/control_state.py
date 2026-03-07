from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SensitiveCheckpointKind(str, Enum):
    OTP = "OTP"
    CAPTCHA = "CAPTCHA"
    PAYMENT_CONFIRMATION = "PAYMENT_CONFIRMATION"
    ADDRESS_CONFIRMATION = "ADDRESS_CONFIRMATION"
    FINAL_PURCHASE_CONFIRMATION = "FINAL_PURCHASE_CONFIRMATION"
    UNKNOWN = "UNKNOWN"


class CheckpointStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class SensitiveCheckpointRequest(BaseModel):
    checkpoint_id: UUID = Field(default_factory=uuid4)
    kind: SensitiveCheckpointKind
    status: CheckpointStatus
    reason: str
    prompt_to_user: str
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None


class LowConfidenceStatus(BaseModel):
    active: bool
    reason: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    ambiguity_notes: list[str] = Field(default_factory=list)
    trust_notes: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    recommended_next_step: str | None = None


class RecoveryKind(str, Enum):
    NAVIGATION_RECOVERY = "NAVIGATION_RECOVERY"
    PAGE_DESYNC = "PAGE_DESYNC"
    MODAL_INTERRUPTION = "MODAL_INTERRUPTION"
    CHECKOUT_BLOCKED = "CHECKOUT_BLOCKED"
    UNKNOWN = "UNKNOWN"


class RecoveryStatus(BaseModel):
    active: bool
    recovery_kind: RecoveryKind | None = None
    reason: str | None = None
    last_attempt_summary: str | None = None
    last_updated_at: datetime | None = None
