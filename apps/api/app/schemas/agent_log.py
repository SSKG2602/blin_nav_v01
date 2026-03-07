from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Contract marker: excerpts must stay redacted-safe and never carry raw secrets.
REDACTION_POLICY: dict[Literal["excerpt_policy"], Any] = {"excerpt_policy": "redacted"}


class AgentStepType(str, Enum):
    PERCEPTION = "perception"
    INTENT_PARSE = "intent_parse"
    NAVIGATION = "navigation"
    VERIFICATION = "verification"
    CHECKOUT = "checkout"
    ERROR = "error"
    META = "meta"


class AgentLogEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    step_type: AgentStepType
    state_before: str | None = None
    state_after: str | None = None
    tool_name: str | None = None
    # Only short summaries; do not store raw secrets or full payloads.
    tool_input_excerpt: str | None = None
    # Only short summaries; do not store raw secrets or full payloads.
    tool_output_excerpt: str | None = None
    low_confidence: bool = False
    human_checkpoint: bool = False
    user_spoken_summary: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
