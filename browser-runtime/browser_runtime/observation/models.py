from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeProductCandidate(BaseModel):
    title: str | None = None
    price_text: str | None = None
    url: str | None = None
    rating_text: str | None = None
    review_count_text: str | None = None
    availability_text: str | None = None
    variant_text: str | None = None
    brand_text: str | None = None
    review_snippets: list[str] = Field(default_factory=list)
    variant_options: list[str] = Field(default_factory=list)


class RuntimePageObservation(BaseModel):
    observed_url: str | None = None
    page_title: str | None = None
    detected_page_hints: list[str] = Field(default_factory=list)
    product_candidates: list[dict] = Field(default_factory=list)
    primary_product: dict | None = None
    cart_items: list[dict] = Field(default_factory=list)
    cart_item_count: int | None = None
    checkout_ready: bool | None = None
    order_id_hint: str | None = None
    order_date_text: str | None = None
    shipping_stage_text: str | None = None
    expected_delivery_text: str | None = None
    order_total_text: str | None = None
    order_card_title: str | None = None
    orders_page_url: str | None = None
    support_entry_hint: str | None = None
    returns_entry_hint: str | None = None
    notes: str | None = None


class RuntimeScreenshotObservation(BaseModel):
    image_base64: str | None = None
    mime_type: str = "image/png"
    source: str = "runtime"
    notes: str | None = None


class RuntimeAmazonAuthStatus(BaseModel):
    connected: bool = False
    cookie_count: int = 0
    current_url: str | None = None
    notes: str | None = None


class RuntimeOrderCancellationResult(BaseModel):
    cancelled: bool
    cancellable: bool | None = None
    order_card_title: str | None = None
    shipping_stage_text: str | None = None
    spoken_summary: str
    notes: str | None = None
