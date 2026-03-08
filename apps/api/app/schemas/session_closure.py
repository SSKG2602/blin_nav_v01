from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.cart_context import CartSnapshot
from app.schemas.purchase_support import FinalPurchaseConfirmation, PostPurchaseSummary


class ClosureAction(BaseModel):
    state: str
    summary: str
    created_at: datetime | None = None


class ClosureCheckpointEntry(BaseModel):
    kind: str
    status: str
    prompt_to_user: str | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None


class FinalSessionArtifact(BaseModel):
    original_goal: str | None = None
    clarified_goal: str | None = None
    chosen_product: str | None = None
    chosen_variant: str | None = None
    quantity_text: str | None = None
    merchant: str | None = None
    trust_status: str | None = None
    warnings: list[str] = Field(default_factory=list)
    important_actions: list[ClosureAction] = Field(default_factory=list)
    cart_snapshot: CartSnapshot | None = None
    checkpoint_history: list[ClosureCheckpointEntry] = Field(default_factory=list)
    final_confirmation: FinalPurchaseConfirmation | None = None
    post_purchase_summary: PostPurchaseSummary | None = None
    spoken_summary: str | None = None
    completed_at: datetime | None = None


class FinalSelfDiagnosis(BaseModel):
    ready_to_close: bool
    unresolved_items: list[str] = Field(default_factory=list)
    fallback_heavy_steps: list[str] = Field(default_factory=list)
    confidence_warnings: list[str] = Field(default_factory=list)
    summary: str
