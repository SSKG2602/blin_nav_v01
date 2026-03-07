from __future__ import annotations

from pydantic import BaseModel


class FinalPurchaseConfirmation(BaseModel):
    required: bool
    confirmed: bool
    prompt_to_user: str | None = None
    confirmation_phrase_expected: str | None = None
    notes: str | None = None


class PostPurchaseSummary(BaseModel):
    order_item_title: str | None = None
    order_price_text: str | None = None
    delivery_window_text: str | None = None
    orders_location_hint: str | None = None
    spoken_summary: str
    notes: str | None = None
