from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class InterruptionMarker(BaseModel):
    active: bool
    interrupted_at: datetime | None = None
    prior_state: str | None = None
    reason: str | None = None
    latest_user_utterance: str | None = None
    resume_summary: str | None = None
