from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ReviewConflictLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ReviewAssessment(BaseModel):
    conflict_level: ReviewConflictLevel
    rating_text: str | None = None
    review_count_text: str | None = None
    review_summary_spoken: str
    conflict_notes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
