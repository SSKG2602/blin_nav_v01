from __future__ import annotations

from pydantic import BaseModel


class LatestOrderSnapshot(BaseModel):
    order_id_hint: str | None = None
    order_date_text: str | None = None
    shipping_stage_text: str | None = None
    expected_delivery_text: str | None = None
    order_total_text: str | None = None
    order_card_title: str | None = None
    orders_page_url: str | None = None
    support_entry_hint: str | None = None
    returns_entry_hint: str | None = None
    spoken_summary: str
    notes: str | None = None


class OrderCancellationResult(BaseModel):
    cancelled: bool
    cancellable: bool | None = None
    order_card_title: str | None = None
    shipping_stage_text: str | None = None
    spoken_summary: str
    notes: str | None = None
