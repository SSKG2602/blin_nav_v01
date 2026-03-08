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


class RuntimePageObservation(BaseModel):
    observed_url: str | None = None
    page_title: str | None = None
    detected_page_hints: list[str] = Field(default_factory=list)
    product_candidates: list[dict] = Field(default_factory=list)
    primary_product: dict | None = None
    cart_item_count: int | None = None
    checkout_ready: bool | None = None
    notes: str | None = None


class RuntimeScreenshotObservation(BaseModel):
    image_base64: str | None = None
    mime_type: str = "image/png"
    source: str = "runtime"
    notes: str | None = None
