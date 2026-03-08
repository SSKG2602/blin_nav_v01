from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClarificationKind(str, Enum):
    INTENT_COMPLETENESS = "INTENT_COMPLETENESS"
    PRODUCT_SELECTION = "PRODUCT_SELECTION"
    PRODUCT_AMBIGUITY = "PRODUCT_AMBIGUITY"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    VARIANT_PRECISION = "VARIANT_PRECISION"
    INTERRUPTION_REANCHOR = "INTERRUPTION_REANCHOR"


class ClarificationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROVIDED_INPUT = "PROVIDED_INPUT"
    CANCELLED = "CANCELLED"


class ClarificationOption(BaseModel):
    label: str
    title: str
    price_text: str | None = None
    variant_text: str | None = None
    difference_summary: str | None = None
    candidate_url: str | None = None


class ClarificationRequest(BaseModel):
    clarification_id: UUID = Field(default_factory=uuid4)
    kind: ClarificationKind
    status: ClarificationStatus
    reason: str
    prompt_to_user: str
    original_user_goal: str | None = None
    candidate_summary: str | None = None
    candidate_options: list[ClarificationOption] = Field(default_factory=list)
    expected_fields: list[str] = Field(default_factory=list)
    resume_state: str | None = None
    clarified_response: str | None = None
    resolution_notes: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None
