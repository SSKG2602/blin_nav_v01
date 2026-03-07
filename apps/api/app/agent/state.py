from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent_log import AgentLogEntry
from app.schemas.session import Merchant


class AgentState(str, Enum):
    SESSION_INITIALIZING = "SESSION_INITIALIZING"
    SEARCHING_PRODUCTS = "SEARCHING_PRODUCTS"
    VIEWING_PRODUCT_DETAIL = "VIEWING_PRODUCT_DETAIL"
    CART_VERIFICATION = "CART_VERIFICATION"
    CHECKOUT_FLOW = "CHECKOUT_FLOW"
    CHECKPOINT_SENSITIVE_ACTION = "CHECKPOINT_SENSITIVE_ACTION"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    LOW_CONFIDENCE_HALT = "LOW_CONFIDENCE_HALT"
    SESSION_CLOSING = "SESSION_CLOSING"
    DONE = "DONE"


class AgentCommandType(str, Enum):
    CALL_LLM_FOR_INTENT = "CALL_LLM_FOR_INTENT"
    NAVIGATE_TO_SEARCH_RESULTS = "NAVIGATE_TO_SEARCH_RESULTS"
    INSPECT_PRODUCT_PAGE = "INSPECT_PRODUCT_PAGE"
    VERIFY_PRODUCT_VARIANT = "VERIFY_PRODUCT_VARIANT"
    REVIEW_CART = "REVIEW_CART"
    PERFORM_CHECKOUT = "PERFORM_CHECKOUT"
    REQUEST_HUMAN_CHECKPOINT = "REQUEST_HUMAN_CHECKPOINT"
    HANDLE_ERROR_RECOVERY = "HANDLE_ERROR_RECOVERY"
    HALT_LOW_CONFIDENCE = "HALT_LOW_CONFIDENCE"
    CLOSE_SESSION = "CLOSE_SESSION"


class AgentCommand(BaseModel):
    type: AgentCommandType
    payload: dict[str, Any] = Field(default_factory=dict)


class UserIntentParsed(BaseModel):
    event_type: Literal["user_intent_parsed"] = "user_intent_parsed"
    intent: str = "search_products"
    query: str | None = None
    merchant: Merchant | None = None


class NavResult(BaseModel):
    event_type: Literal["nav_result"] = "nav_result"
    success: bool = True
    page_type: str | None = None
    confidence: float | None = None


class VerificationResult(BaseModel):
    event_type: Literal["verification_result"] = "verification_result"
    success: bool = True
    low_confidence: bool = False
    notes: str | None = None


class CheckoutProgress(BaseModel):
    event_type: Literal["checkout_progress"] = "checkout_progress"
    proceed_to_checkout: bool = True
    sensitive_step_required: bool = False
    completed: bool = False
    low_confidence: bool = False


class HumanCheckpointResolved(BaseModel):
    event_type: Literal["human_checkpoint_resolved"] = "human_checkpoint_resolved"
    approved: bool


class LowConfidenceTriggered(BaseModel):
    event_type: Literal["low_confidence_triggered"] = "low_confidence_triggered"
    reason: str | None = None


class ToolError(BaseModel):
    event_type: Literal["tool_error"] = "tool_error"
    error_type: str = "tool_error"
    error_message: str


class SessionCloseRequested(BaseModel):
    event_type: Literal["session_close_requested"] = "session_close_requested"


AgentEvent = Annotated[
    UserIntentParsed
    | NavResult
    | VerificationResult
    | CheckoutProgress
    | HumanCheckpointResolved
    | LowConfidenceTriggered
    | ToolError
    | SessionCloseRequested,
    Field(discriminator="event_type"),
]


class AgentTransitionResult(BaseModel):
    new_state: AgentState
    commands: list[AgentCommand] = Field(default_factory=list)
    log_entries: list[AgentLogEntry] = Field(default_factory=list)
    spoken_summary: str | None = None
    debug_notes: str | None = None
