from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MultimodalDecision(str, Enum):
    PROCEED = "PROCEED"
    REQUIRE_USER_CONFIRMATION = "REQUIRE_USER_CONFIRMATION"
    REQUIRE_SENSITIVE_CHECKPOINT = "REQUIRE_SENSITIVE_CHECKPOINT"
    HALT_LOW_CONFIDENCE = "HALT_LOW_CONFIDENCE"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MultimodalAssessment(BaseModel):
    decision: MultimodalDecision
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_band: ConfidenceBand
    needs_user_confirmation: bool
    needs_sensitive_checkpoint: bool
    should_halt_low_confidence: bool
    ambiguity_notes: list[str] = Field(default_factory=list)
    trust_notes: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    reasoning_summary: str
    recommended_next_step: str | None = None
    notes: str | None = None
