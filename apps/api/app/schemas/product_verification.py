from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ProductIntentSpec(BaseModel):
    raw_query: str
    brand: str | None = None
    product_name: str | None = None
    quantity_text: str | None = None
    size_text: str | None = None
    color: str | None = None
    variant: str | None = None


class VerificationDecision(str, Enum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ProductVerificationResult(BaseModel):
    decision: VerificationDecision
    matched_fields: list[str] = Field(default_factory=list)
    mismatched_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    user_safe_summary: str
    notes: str | None = None

