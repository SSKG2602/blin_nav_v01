from app.llm.gemini_service import GeminiIntentSummaryService
from app.schemas.intent import ShoppingAction
from app.schemas.multimodal_assessment import MultimodalDecision
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.product_verification import (
    ProductIntentSpec,
    ProductVerificationResult,
    VerificationDecision,
)


def test_fallback_intent_parsing_for_search_query() -> None:
    service = GeminiIntentSummaryService(api_key="")
    result = service.interpret_user_intent("Find Pedigree dog food 3kg on amazon")

    assert result.action == ShoppingAction.SEARCH_PRODUCT
    assert result.merchant == "amazon.in"
    assert result.product_intent is not None
    assert result.product_intent.brand == "pedigree"
    assert result.product_intent.size_text == "3kg"
    assert result.requires_clarification is False


def test_fallback_intent_parsing_for_cancel_and_checkout() -> None:
    service = GeminiIntentSummaryService(api_key="")

    cancel_intent = service.interpret_user_intent("cancel this flow")
    checkout_intent = service.interpret_user_intent("please proceed to checkout now")

    assert cancel_intent.action == ShoppingAction.CANCEL
    assert checkout_intent.action == ShoppingAction.PROCEED_CHECKOUT


def test_fallback_intent_parsing_supports_hindi_keywords() -> None:
    service = GeminiIntentSummaryService(api_key="")

    search_intent = service.interpret_user_intent("amazon पर pedigree dog food 3kg खोजो")
    checkout_intent = service.interpret_user_intent("checkout करो")

    assert search_intent.action == ShoppingAction.SEARCH_PRODUCT
    assert search_intent.merchant == "amazon.in"
    assert search_intent.product_intent is not None
    assert search_intent.product_intent.size_text == "3kg"
    assert checkout_intent.action == ShoppingAction.PROCEED_CHECKOUT


def test_fallback_when_gemini_sdk_or_key_missing() -> None:
    service = GeminiIntentSummaryService(api_key="")
    result = service.interpret_user_intent("search for dog food")

    assert service._gemini_client is None
    assert "Fallback intent parse" in (result.notes or "")
    assert result.confidence <= 0.9


def test_summary_generation_for_strong_verification_match() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        page_title="Pedigree Adult Dog Food",
        primary_product=ProductCandidate(title="Pedigree Adult Dog Food", price_text="₹799"),
        confidence=0.85,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.MATCH,
        matched_fields=["brand", "product_name", "size_text"],
        mismatched_fields=[],
        missing_fields=[],
        confidence=0.88,
        user_safe_summary="This product appears to match your request.",
    )

    summary = service.summarize_page_and_verification(page, verification)
    assert "strong match" in summary.lower()
    assert "confirm" in summary.lower()


def test_summary_generation_for_partial_or_ambiguous_verification() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        page_title="Pedigree Adult Dog Food",
        primary_product=ProductCandidate(title="Pedigree Adult Dog Food"),
        confidence=0.72,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.AMBIGUOUS,
        matched_fields=["brand"],
        mismatched_fields=[],
        missing_fields=["variant"],
        confidence=0.42,
        user_safe_summary="I found a possible product, but key variant details are unclear.",
    )

    summary = service.summarize_page_and_verification(page, verification)
    assert "possible match" in summary.lower()
    assert "confirmation" in summary.lower()


def test_summary_generation_for_insufficient_evidence() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.UNKNOWN,
        page_title="Unknown",
        confidence=0.25,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
        matched_fields=[],
        mismatched_fields=[],
        missing_fields=["brand", "product_name"],
        confidence=0.20,
        user_safe_summary="I do not have enough evidence to verify this item safely.",
    )

    summary = service.summarize_page_and_verification(page, verification)
    assert "enough evidence" in summary.lower()


def test_multimodal_fallback_proceed_case() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        page_title="Pedigree Adult Dog Food 3kg",
        primary_product=ProductCandidate(title="Pedigree Adult Dog Food 3kg", price_text="₹799"),
        confidence=0.88,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.MATCH,
        matched_fields=["brand", "product_name", "size_text"],
        mismatched_fields=[],
        missing_fields=[],
        confidence=0.9,
        user_safe_summary="Strong match detected.",
    )

    assessment = service.analyze_multimodal_assessment(
        intent=ProductIntentSpec(raw_query="pedigree dog food 3kg", brand="pedigree", product_name="dog food"),
        page=page,
        verification=verification,
        spoken_summary="Strong match on product detail page.",
    )
    assert assessment.decision == MultimodalDecision.PROCEED
    assert assessment.should_halt_low_confidence is False
    assert assessment.reasoning_summary


def test_multimodal_fallback_requires_confirmation_for_ambiguous_case() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.PRODUCT_DETAIL,
        page_title="Pedigree Dog Food",
        primary_product=ProductCandidate(title="Pedigree Dog Food"),
        confidence=0.68,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.AMBIGUOUS,
        matched_fields=["brand"],
        mismatched_fields=[],
        missing_fields=["variant"],
        confidence=0.42,
        user_safe_summary="Possible match, variant unclear.",
    )

    assessment = service.analyze_multimodal_assessment(
        intent=ProductIntentSpec(raw_query="pedigree dog food puppy", brand="pedigree", variant="puppy"),
        page=page,
        verification=verification,
        spoken_summary=None,
    )
    assert assessment.decision == MultimodalDecision.REQUIRE_USER_CONFIRMATION
    assert assessment.needs_user_confirmation is True


def test_multimodal_fallback_sensitive_checkpoint_for_checkout_context() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.CHECKOUT,
        page_title="Checkout",
        checkout_ready=True,
        confidence=0.8,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.MATCH,
        matched_fields=["product_name"],
        mismatched_fields=[],
        missing_fields=[],
        confidence=0.82,
        user_safe_summary="Looks like the expected item.",
    )

    assessment = service.analyze_multimodal_assessment(
        intent=ProductIntentSpec(raw_query="dog food", product_name="dog food"),
        page=page,
        verification=verification,
        spoken_summary="Checkout ready.",
    )
    assert assessment.decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT
    assert assessment.needs_sensitive_checkpoint is True


def test_multimodal_fallback_halts_for_insufficient_evidence() -> None:
    service = GeminiIntentSummaryService(api_key="")
    page = PageUnderstanding(
        page_type=PageType.UNKNOWN,
        page_title="Unknown",
        confidence=0.15,
    )
    verification = ProductVerificationResult(
        decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
        matched_fields=[],
        mismatched_fields=[],
        missing_fields=["brand", "product_name"],
        confidence=0.18,
        user_safe_summary="Insufficient evidence.",
    )

    assessment = service.analyze_multimodal_assessment(
        intent=None,
        page=page,
        verification=verification,
        spoken_summary=None,
    )
    assert assessment.decision == MultimodalDecision.HALT_LOW_CONFIDENCE
    assert assessment.should_halt_low_confidence is True


def test_visual_page_analysis_fallback_without_gemini() -> None:
    service = GeminiIntentSummaryService(api_key="")
    result = service.analyze_visual_page(
        raw_observation={
            "detected_page_hints": ["search_results"],
            "page_title": "Results",
        },
        screenshot={"image_base64": "ZmFrZQ==", "mime_type": "image/png"},
    )

    assert result["page_type"] == "SEARCH_RESULTS"
    assert isinstance(result.get("notes"), str)


def test_visual_page_analysis_fallback_unknown_when_hints_missing() -> None:
    service = GeminiIntentSummaryService(api_key="")
    result = service.analyze_visual_page(
        raw_observation={"page_title": "Unknown"},
        screenshot=None,
    )

    assert result["page_type"] == "UNKNOWN"
    assert "Fallback visual reasoning" in str(result.get("notes"))
