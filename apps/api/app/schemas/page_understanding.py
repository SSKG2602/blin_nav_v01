from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PageType(str, Enum):
    HOME = "HOME"
    SEARCH_RESULTS = "SEARCH_RESULTS"
    PRODUCT_DETAIL = "PRODUCT_DETAIL"
    CART = "CART"
    CHECKOUT = "CHECKOUT"
    UNKNOWN = "UNKNOWN"


class ProductCandidate(BaseModel):
    title: str | None = None
    price_text: str | None = None
    url: str | None = None
    summary_text: str | None = None
    quantity_text: str | None = None
    rating_text: str | None = None
    review_count_text: str | None = None
    availability_text: str | None = None
    variant_text: str | None = None
    brand_text: str | None = None
    review_snippets: list[str] = Field(default_factory=list)
    variant_options: list[str] = Field(default_factory=list)


class PageUnderstanding(BaseModel):
    page_type: PageType
    page_title: str | None = None
    product_candidates: list[ProductCandidate] = Field(default_factory=list)
    primary_product: ProductCandidate | None = None
    cart_item_count: int | None = None
    checkout_ready: bool | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None
