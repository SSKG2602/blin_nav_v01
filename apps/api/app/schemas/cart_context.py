from __future__ import annotations

from pydantic import BaseModel, Field


class CartItemContext(BaseModel):
    item_id: str
    title: str | None = None
    price_text: str | None = None
    quantity_text: str | None = None
    variant_text: str | None = None
    url: str | None = None
    merchant_item_ref: str | None = None
    notes: str | None = None


class CartSnapshot(BaseModel):
    items: list[CartItemContext] = Field(default_factory=list)
    cart_item_count: int | None = None
    checkout_ready: bool | None = None
    currency_text: str | None = None
    notes: str | None = None
