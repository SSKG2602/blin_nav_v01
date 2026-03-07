from __future__ import annotations

from typing import Protocol

from app.schemas.intent import InterpretedUserIntent
from app.schemas.multimodal_assessment import MultimodalAssessment
from app.schemas.page_understanding import PageUnderstanding
from app.schemas.product_verification import ProductIntentSpec, ProductVerificationResult


class BlindNavLLMClient(Protocol):
    def interpret_user_intent(self, utterance: str) -> InterpretedUserIntent:
        ...

    def summarize_page_and_verification(
        self,
        page: PageUnderstanding,
        verification: ProductVerificationResult | None,
    ) -> str:
        ...

    def analyze_multimodal_assessment(
        self,
        *,
        intent: ProductIntentSpec | None,
        page: PageUnderstanding | None,
        verification: ProductVerificationResult | None,
        spoken_summary: str | None = None,
    ) -> MultimodalAssessment:
        ...
