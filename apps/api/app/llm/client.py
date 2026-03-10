from __future__ import annotations

from typing import Protocol

from app.schemas.intent import InterpretedUserIntent
from app.schemas.multimodal_assessment import MultimodalAssessment
from app.schemas.page_understanding import PageUnderstanding
from app.schemas.product_verification import ProductIntentSpec, ProductVerificationResult


class BlindNavLLMClient(Protocol):
    def interpret_user_intent(self, utterance: str) -> InterpretedUserIntent:
        ...

    def score_product_candidates(
        self,
        *,
        query: str,
        candidates: list[dict[str, object]],
    ) -> int | None:
        """
        Given a user query and a short list of product candidate dicts
        (each with 'title', 'url', 'price_text'), returns the 0-based index
        of the best match according to Gemini.
        Returns None if Gemini is unavailable, the call fails, or the
        result is ambiguous. Callers must handle None gracefully.
        """
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

    def analyze_visual_page(
        self,
        *,
        raw_observation: dict[str, object],
        screenshot: dict[str, object] | None,
    ) -> dict[str, object]:
        ...
