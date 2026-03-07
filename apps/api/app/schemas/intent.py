from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.product_verification import ProductIntentSpec


class ShoppingAction(str, Enum):
    SEARCH_PRODUCT = "SEARCH_PRODUCT"
    REFINE_RESULTS = "REFINE_RESULTS"
    SELECT_PRODUCT = "SELECT_PRODUCT"
    ADD_TO_CART = "ADD_TO_CART"
    PROCEED_CHECKOUT = "PROCEED_CHECKOUT"
    CANCEL = "CANCEL"
    UNKNOWN = "UNKNOWN"


class InterpretedUserIntent(BaseModel):
    raw_utterance: str
    action: ShoppingAction
    merchant: str | None = None
    product_intent: ProductIntentSpec | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    requires_clarification: bool
    spoken_confirmation: str
    notes: str | None = None

