from __future__ import annotations

import re
from urllib.parse import urlparse

from app.schemas.control_state import (
    CheckpointStatus,
    SensitiveCheckpointKind,
    SensitiveCheckpointRequest,
)
from app.schemas.multimodal_assessment import MultimodalAssessment, MultimodalDecision
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.purchase_support import FinalPurchaseConfirmation, PostPurchaseSummary
from app.schemas.review_analysis import ReviewAssessment, ReviewConflictLevel
from app.schemas.trust_verification import TrustAssessment, TrustStatus

_MERCHANT_ALLOWLIST: dict[str, set[str]] = {
    "amazon.in": {"amazon.in", "www.amazon.in", "m.amazon.in"},
    "flipkart.com": {"flipkart.com", "www.flipkart.com"},
    "meesho.com": {"meesho.com", "www.meesho.com"},
}

_LOOKALIKE_PATTERNS = (
    "amaz0n",
    "arnazon",
    "amazn",
    "flipkarrt",
    "fl1pkart",
    "meesh0",
    "rnazon",
)

_RATING_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")


def _safe_text(value: str | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _extract_domain(url: str | None) -> str | None:
    text = _safe_text(url)
    if not text:
        return None
    try:
        parsed = urlparse(text)
    except Exception:
        return None
    host = (parsed.hostname or "").lower().strip()
    return host or None


def _is_https(url: str | None) -> bool | None:
    text = _safe_text(url)
    if not text:
        return None
    try:
        parsed = urlparse(text)
    except Exception:
        return None
    if not parsed.scheme:
        return None
    return parsed.scheme.lower() == "https"


def _merchant_from_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    for merchant, domains in _MERCHANT_ALLOWLIST.items():
        if domain in domains:
            return merchant
    return None


def _known_match(domain: str | None, expected_merchant: str | None) -> bool | None:
    if expected_merchant is None:
        return None
    expected = expected_merchant.lower().strip()
    if not expected:
        return None
    allowed_domains = _MERCHANT_ALLOWLIST.get(expected)
    if not allowed_domains:
        return None
    if domain is None:
        return False
    return domain in allowed_domains


def _lookalike_risk(domain: str | None) -> bool | None:
    if domain is None:
        return None
    lower = domain.lower()
    if any(token in lower for token in _LOOKALIKE_PATTERNS):
        return True
    if "amazon" in lower and "amazon.in" not in lower:
        return True
    if "flipkart" in lower and "flipkart.com" not in lower:
        return True
    if "meesho" in lower and "meesho.com" not in lower:
        return True
    return False


def derive_trust_assessment(
    *,
    observation: dict[str, object] | None,
    expected_merchant: str | None,
) -> TrustAssessment:
    raw_url = None
    if isinstance(observation, dict):
        raw_url = observation.get("observed_url") or observation.get("url")
    url_text = _safe_text(raw_url) if isinstance(raw_url, str) else None
    domain = _extract_domain(url_text)
    https_present = _is_https(url_text)
    merchant_from_domain = _merchant_from_domain(domain)
    known_merchant_match = _known_match(domain, expected_merchant)
    lookalike_risk = _lookalike_risk(domain)
    merchant = expected_merchant or merchant_from_domain

    if (
        known_merchant_match is True
        and https_present is True
        and lookalike_risk is False
    ):
        status = TrustStatus.TRUSTED
        reasoning = "Merchant domain and HTTPS checks are aligned with trusted patterns."
        notes = None
    elif lookalike_risk is True or https_present is False:
        status = TrustStatus.SUSPICIOUS
        reasoning = "Trust checks found suspicious domain or transport signals."
        notes = "Proceed only with explicit confirmation."
    else:
        status = TrustStatus.UNVERIFIED
        reasoning = "Trust checks are inconclusive with current URL evidence."
        notes = "Additional verification recommended."

    return TrustAssessment(
        status=status,
        merchant=merchant,
        domain=domain,
        https_present=https_present,
        lookalike_risk=lookalike_risk,
        known_merchant_match=known_merchant_match,
        reasoning_summary=reasoning,
        notes=notes,
    )


def _candidate_for_reviews(page: PageUnderstanding | None) -> ProductCandidate | None:
    if page is None:
        return None
    if page.primary_product is not None:
        return page.primary_product
    if page.product_candidates:
        return page.product_candidates[0]
    return None


def _parse_rating(value: str | None) -> float | None:
    text = _safe_text(value)
    if not text:
        return None
    match = _RATING_PATTERN.search(text)
    if not match:
        return None
    try:
        rating = float(match.group(1))
    except ValueError:
        return None
    if rating <= 0 or rating > 5:
        return None
    return rating


def _parse_review_count(value: str | None) -> int | None:
    text = _safe_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def derive_review_assessment(
    *,
    page: PageUnderstanding | None,
    multimodal_assessment: MultimodalAssessment | None = None,
) -> ReviewAssessment:
    candidate = _candidate_for_reviews(page)
    rating_text = candidate.rating_text if candidate is not None else None
    review_count_text = candidate.review_count_text if candidate is not None else None
    rating_value = _parse_rating(rating_text)
    review_count = _parse_review_count(review_count_text)
    notes: list[str] = []

    has_ambiguity_from_multimodal = False
    if multimodal_assessment is not None:
        has_ambiguity_from_multimodal = any(
            "review" in note.lower() or "conflict" in note.lower()
            for note in multimodal_assessment.ambiguity_notes
        )

    if rating_value is None and review_count is None:
        level = ReviewConflictLevel.UNKNOWN
        confidence = 0.25
        notes.append("Review signals are unavailable.")
    elif has_ambiguity_from_multimodal:
        level = ReviewConflictLevel.HIGH
        confidence = 0.55
        notes.append("Multimodal ambiguity notes include review conflict signals.")
    elif rating_value is not None and rating_value < 3.4:
        level = ReviewConflictLevel.HIGH
        confidence = 0.72 if review_count and review_count >= 40 else 0.6
        notes.append("Rating appears low for product confidence.")
    elif rating_value is not None and rating_value < 4.1:
        level = ReviewConflictLevel.MEDIUM
        confidence = 0.62
        notes.append("Rating appears moderate; user confirmation is recommended.")
    elif review_count is not None and review_count < 40:
        level = ReviewConflictLevel.MEDIUM
        confidence = 0.56
        notes.append("Review count is limited; confidence is moderate.")
    else:
        level = ReviewConflictLevel.LOW
        confidence = 0.76
        notes.append("Rating and review volume appear consistent.")

    if level == ReviewConflictLevel.HIGH:
        summary = "Review signals look risky or conflicting. Please confirm before proceeding."
    elif level == ReviewConflictLevel.MEDIUM:
        summary = "Review signals are mixed. A confirmation checkpoint is recommended."
    elif level == ReviewConflictLevel.LOW:
        summary = "Review signals look generally consistent, but final confirmation is still advised."
    else:
        summary = "I do not have enough review evidence to assess conflicts safely yet."

    return ReviewAssessment(
        conflict_level=level,
        rating_text=rating_text,
        review_count_text=review_count_text,
        review_summary_spoken=summary,
        conflict_notes=notes,
        confidence=confidence,
    )


def derive_final_purchase_confirmation(
    *,
    checkpoint: SensitiveCheckpointRequest | None,
    multimodal_assessment: MultimodalAssessment | None,
    page: PageUnderstanding | None,
    previous_confirmation: FinalPurchaseConfirmation | None = None,
) -> FinalPurchaseConfirmation:
    if checkpoint is not None:
        if checkpoint.status == CheckpointStatus.PENDING:
            return FinalPurchaseConfirmation(
                required=True,
                confirmed=False,
                prompt_to_user=checkpoint.prompt_to_user,
                confirmation_phrase_expected="confirm purchase",
                notes=f"Checkpoint pending: {checkpoint.kind.value}",
            )
        if checkpoint.status == CheckpointStatus.APPROVED:
            return FinalPurchaseConfirmation(
                required=True,
                confirmed=True,
                prompt_to_user=None,
                confirmation_phrase_expected="confirm purchase",
                notes=f"Checkpoint approved: {checkpoint.kind.value}",
            )
        if checkpoint.status in {CheckpointStatus.REJECTED, CheckpointStatus.CANCELLED, CheckpointStatus.EXPIRED}:
            return FinalPurchaseConfirmation(
                required=True,
                confirmed=False,
                prompt_to_user="User rejected confirmation; do not proceed.",
                confirmation_phrase_expected="confirm purchase",
                notes=f"Checkpoint status: {checkpoint.status.value}",
            )

    if (
        multimodal_assessment is not None
        and multimodal_assessment.decision == MultimodalDecision.REQUIRE_SENSITIVE_CHECKPOINT
    ):
        return FinalPurchaseConfirmation(
            required=True,
            confirmed=False,
            prompt_to_user="Final purchase confirmation required before continuing.",
            confirmation_phrase_expected="confirm purchase",
            notes="Derived from multimodal sensitive checkpoint decision.",
        )

    if page is not None and page.page_type == PageType.CHECKOUT and page.checkout_ready is True:
        return FinalPurchaseConfirmation(
            required=True,
            confirmed=False,
            prompt_to_user="Checkout is ready. Please confirm final purchase.",
            confirmation_phrase_expected="confirm purchase",
            notes="Checkout-like state detected.",
        )

    if previous_confirmation is not None and previous_confirmation.confirmed:
        return previous_confirmation

    return FinalPurchaseConfirmation(
        required=False,
        confirmed=False,
        prompt_to_user=None,
        confirmation_phrase_expected="confirm purchase",
        notes="No final purchase checkpoint currently required.",
    )


def derive_post_purchase_summary(
    *,
    page: PageUnderstanding | None,
    observation: dict[str, object] | None,
    trust_assessment: TrustAssessment | None = None,
) -> PostPurchaseSummary:
    page_title = _safe_text(page.page_title if page is not None else None).lower()
    raw_notes = ""
    if isinstance(observation, dict):
        note_val = observation.get("notes")
        if isinstance(note_val, str):
            raw_notes = note_val.lower()

    confirmation_like = any(
        token in page_title or token in raw_notes
        for token in ("order", "thank you", "confirmed", "placed")
    )
    candidate = _candidate_for_reviews(page)

    if confirmation_like:
        title = candidate.title if candidate is not None else None
        price = candidate.price_text if candidate is not None else None
        delivery = None
        if isinstance(observation, dict):
            delivery_raw = observation.get("delivery_window_text")
            if isinstance(delivery_raw, str):
                delivery = delivery_raw.strip() or None

        spoken = "Order confirmation appears on screen."
        if title:
            spoken = f"Order appears placed for {title}."

        return PostPurchaseSummary(
            order_item_title=title,
            order_price_text=price,
            delivery_window_text=delivery,
            orders_location_hint="Check Orders in your merchant account profile.",
            spoken_summary=spoken,
            notes="Derived from order-confirmation-like page signals.",
        )

    trust_note = ""
    if trust_assessment is not None and trust_assessment.status != TrustStatus.TRUSTED:
        trust_note = " Trust status is not fully trusted."

    return PostPurchaseSummary(
        order_item_title=None,
        order_price_text=None,
        delivery_window_text=None,
        orders_location_hint="Open Orders page after confirmation.",
        spoken_summary="Post-purchase confirmation is not visible yet.",
        notes=f"Weak post-purchase evidence.{trust_note}".strip(),
    )
