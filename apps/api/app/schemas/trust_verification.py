from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class TrustStatus(str, Enum):
    TRUSTED = "TRUSTED"
    SUSPICIOUS = "SUSPICIOUS"
    UNVERIFIED = "UNVERIFIED"


class TrustAssessment(BaseModel):
    status: TrustStatus
    merchant: str | None = None
    domain: str | None = None
    https_present: bool | None = None
    lookalike_risk: bool | None = None
    known_merchant_match: bool | None = None
    reasoning_summary: str
    notes: str | None = None
