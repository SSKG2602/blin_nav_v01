from __future__ import annotations

import re

from app.schemas.page_understanding import ProductCandidate
from app.schemas.product_verification import (
    ProductIntentSpec,
    ProductVerificationResult,
    VerificationDecision,
)

_NON_WORD_RE = re.compile(r"[^a-z0-9\s]")
_SIZE_RE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:kg|g|gm|ml|l|litre|litres)\b", re.IGNORECASE)
_PACK_RE = re.compile(
    r"\b(?:pack of \d+|\d+\s?(?:pack|packs|count|pcs|pc|x))\b",
    re.IGNORECASE,
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = _NON_WORD_RE.sub(" ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value.strip())
    return ordered


def _contains_phrase(expected: str, observed: str) -> bool:
    expected_norm = _normalize_text(expected)
    observed_norm = _normalize_text(observed)
    if not expected_norm or not observed_norm:
        return False
    return expected_norm in observed_norm


def _token_overlap_ratio(expected: str, observed: str) -> float:
    expected_tokens = {token for token in _normalize_text(expected).split() if token}
    observed_tokens = {token for token in _normalize_text(observed).split() if token}
    if not expected_tokens or not observed_tokens:
        return 0.0
    overlap = expected_tokens.intersection(observed_tokens)
    return len(overlap) / len(expected_tokens)


def _collect_observed_text(candidate: ProductCandidate | None) -> str:
    if candidate is None:
        return ""
    return " ".join(
        part
        for part in [
            candidate.brand_text,
            candidate.title,
            candidate.variant_text,
            candidate.availability_text,
            candidate.price_text,
        ]
        if part
    )


def _available_variant_options(candidate: ProductCandidate | None) -> list[str]:
    if candidate is None:
        return []
    return _dedupe(list(candidate.variant_options or []))


def _extract_variant_like(expected_value: str | None) -> str | None:
    if not expected_value:
        return None
    text = expected_value.strip()
    return text or None


def _extract_size_terms(text: str) -> list[str]:
    return _dedupe([match.group(0) for match in _SIZE_RE.finditer(text or "")])


def _extract_pack_terms(text: str) -> list[str]:
    return _dedupe([match.group(0) for match in _PACK_RE.finditer(text or "")])


def _nearest_option(expected: str, options: list[str]) -> str | None:
    best: tuple[float, str] | None = None
    for option in options:
        overlap = _token_overlap_ratio(expected, option)
        if overlap <= 0:
            continue
        if best is None or overlap > best[0]:
            best = (overlap, option)
    if best is None:
        return None
    return best[1]


def _variant_comparison_summary(
    *,
    expected_variant_text: str | None,
    selected_variant_text: str | None,
    available_variant_options: list[str],
) -> str | None:
    if not expected_variant_text:
        return None
    if selected_variant_text and _contains_phrase(expected_variant_text, selected_variant_text):
        return f"Selected variant matches the requested option: {selected_variant_text}."
    nearest = _nearest_option(expected_variant_text, available_variant_options)
    if nearest and _normalize_text(nearest) != _normalize_text(expected_variant_text):
        return f"Requested variant: {expected_variant_text}. Nearest available option: {nearest}."
    if selected_variant_text:
        return f"Requested variant: {expected_variant_text}. Current selection reads as {selected_variant_text}."
    if available_variant_options:
        return (
            f"Requested variant: {expected_variant_text}. "
            f"Visible options: {', '.join(available_variant_options[:4])}."
        )
    return f"Requested variant: {expected_variant_text}, but the page did not expose a clear selected option."


def _build_user_summary(
    *,
    decision: VerificationDecision,
    matched_fields: list[str],
    mismatched_fields: list[str],
    missing_fields: list[str],
    comparison_summary: str | None,
) -> str:
    if decision == VerificationDecision.MATCH:
        if comparison_summary:
            return f"This product appears to match your request. {comparison_summary}"
        return "This product appears to match your request."
    if decision == VerificationDecision.PARTIAL_MATCH:
        return (
            "This is a partial match. "
            f"Matched fields: {', '.join(matched_fields) or 'none'}. "
            f"Mismatches: {', '.join(mismatched_fields) or 'none'}. "
            f"{comparison_summary or ''}".strip()
        )
    if decision == VerificationDecision.MISMATCH:
        return (
            "This product does not match your request. "
            f"Mismatched fields: {', '.join(mismatched_fields) or 'unspecified'}. "
            f"{comparison_summary or ''}".strip()
        )
    if decision == VerificationDecision.AMBIGUOUS:
        return (
            "I found a possible product, but key details are still unclear. "
            f"Please confirm: {', '.join(missing_fields) or 'variant details'}. "
            f"{comparison_summary or ''}".strip()
        )
    return "I do not have enough evidence to verify this item safely."


def verify_product_against_intent(
    intent: ProductIntentSpec,
    candidate: ProductCandidate | None,
) -> ProductVerificationResult:
    requested_fields: dict[str, str] = {}
    for field_name in ("brand", "product_name", "quantity_text", "size_text", "color", "variant"):
        value = getattr(intent, field_name)
        if isinstance(value, str) and value.strip():
            requested_fields[field_name] = value.strip()

    if candidate is None:
        missing = list(requested_fields.keys()) or ["raw_query"]
        return ProductVerificationResult(
            decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
            matched_fields=[],
            mismatched_fields=[],
            missing_fields=missing,
            confidence=0.15,
            user_safe_summary=_build_user_summary(
                decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
                matched_fields=[],
                mismatched_fields=[],
                missing_fields=missing,
                comparison_summary=None,
            ),
            notes="No product candidate was available for comparison.",
        )

    observed_text = _collect_observed_text(candidate)
    observed_norm = _normalize_text(observed_text)
    available_variant_options = _available_variant_options(candidate)
    selected_variant_text = candidate.variant_text
    expected_variant_text = _extract_variant_like(
        intent.variant or intent.size_text or intent.quantity_text or intent.color
    )
    overall_overlap = _token_overlap_ratio(intent.raw_query, observed_text)

    if not observed_norm:
        missing = list(requested_fields.keys()) or ["raw_query"]
        return ProductVerificationResult(
            decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
            matched_fields=[],
            mismatched_fields=[],
            missing_fields=missing,
            expected_variant_text=expected_variant_text,
            selected_variant_text=selected_variant_text,
            available_variant_options=available_variant_options,
            confidence=0.20,
            user_safe_summary=_build_user_summary(
                decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
                matched_fields=[],
                mismatched_fields=[],
                missing_fields=missing,
                comparison_summary=None,
            ),
            notes="Candidate did not include enough text for safe verification.",
        )

    if not requested_fields:
        overlap_ratio = _token_overlap_ratio(intent.raw_query, observed_text)
        if overlap_ratio >= 0.6:
            return ProductVerificationResult(
                decision=VerificationDecision.PARTIAL_MATCH,
                matched_fields=["raw_query"],
                mismatched_fields=[],
                missing_fields=[],
                expected_variant_text=expected_variant_text,
                selected_variant_text=selected_variant_text,
                available_variant_options=available_variant_options,
                comparison_summary=None,
                confidence=0.60,
                user_safe_summary=_build_user_summary(
                    decision=VerificationDecision.PARTIAL_MATCH,
                    matched_fields=["raw_query"],
                    mismatched_fields=[],
                    missing_fields=[],
                    comparison_summary=None,
                ),
                notes="Only raw query was available; using token overlap.",
            )
        if overlap_ratio > 0.0:
            return ProductVerificationResult(
                decision=VerificationDecision.AMBIGUOUS,
                matched_fields=[],
                mismatched_fields=[],
                missing_fields=["raw_query"],
                expected_variant_text=expected_variant_text,
                selected_variant_text=selected_variant_text,
                available_variant_options=available_variant_options,
                comparison_summary=None,
                confidence=0.35,
                user_safe_summary=_build_user_summary(
                    decision=VerificationDecision.AMBIGUOUS,
                    matched_fields=[],
                    mismatched_fields=[],
                    missing_fields=["raw_query"],
                    comparison_summary=None,
                ),
                notes="Raw query partially overlaps with candidate text.",
            )
        return ProductVerificationResult(
            decision=VerificationDecision.MISMATCH,
            matched_fields=[],
            mismatched_fields=["raw_query"],
            missing_fields=[],
            expected_variant_text=expected_variant_text,
            selected_variant_text=selected_variant_text,
            available_variant_options=available_variant_options,
            comparison_summary=None,
            confidence=0.70,
            user_safe_summary=_build_user_summary(
                decision=VerificationDecision.MISMATCH,
                matched_fields=[],
                mismatched_fields=["raw_query"],
                missing_fields=[],
                comparison_summary=None,
            ),
            notes="Raw query has no meaningful overlap with candidate text.",
        )

    matched_fields: list[str] = []
    mismatched_fields: list[str] = []
    missing_fields: list[str] = []

    for field_name, expected_value in requested_fields.items():
        if _contains_phrase(expected_value, observed_text):
            matched_fields.append(field_name)
            continue

        if field_name == "brand":
            if candidate.brand_text and _contains_phrase(expected_value, candidate.brand_text):
                matched_fields.append(field_name)
                continue
            mismatched_fields.append(field_name)
            continue

        if field_name == "product_name":
            overlap = _token_overlap_ratio(expected_value, candidate.title or observed_text)
            if overlap >= 0.6:
                matched_fields.append(field_name)
                continue
            mismatched_fields.append(field_name)
            continue

        if field_name in {"size_text", "quantity_text"}:
            if selected_variant_text and _contains_phrase(expected_value, selected_variant_text):
                matched_fields.append(field_name)
                continue
            extracted_terms = (
                _extract_size_terms(observed_text)
                + _extract_pack_terms(observed_text)
                + _extract_size_terms(selected_variant_text)
                + _extract_pack_terms(selected_variant_text)
            )
            visible_terms: list[str] = []
            for option in available_variant_options:
                visible_terms.extend(_extract_size_terms(option))
                visible_terms.extend(_extract_pack_terms(option))
            nearest = _nearest_option(expected_value, extracted_terms)
            nearest_visible = _nearest_option(expected_value, visible_terms)
            if nearest and _normalize_text(nearest) == _normalize_text(expected_value):
                matched_fields.append(field_name)
                continue
            if nearest_visible and _normalize_text(nearest_visible) == _normalize_text(expected_value):
                mismatched_fields.append(field_name)
                continue
            if nearest:
                mismatched_fields.append(field_name)
                continue
            missing_fields.append(field_name)
            continue

        if field_name in {"variant", "color"}:
            if selected_variant_text and _contains_phrase(expected_value, selected_variant_text):
                matched_fields.append(field_name)
                continue
            nearest_option = _nearest_option(expected_value, available_variant_options)
            if nearest_option and _normalize_text(nearest_option) == _normalize_text(expected_value):
                matched_fields.append(field_name)
                continue
            if nearest_option:
                mismatched_fields.append(field_name)
                continue
            missing_fields.append(field_name)
            continue

        missing_fields.append(field_name)

    comparison_summary = _variant_comparison_summary(
        expected_variant_text=expected_variant_text,
        selected_variant_text=selected_variant_text,
        available_variant_options=available_variant_options,
    )

    variant_like_fields = {"variant", "size_text", "quantity_text", "color"}
    brand_mismatch = "brand" in mismatched_fields
    product_name_mismatch = "product_name" in mismatched_fields
    variant_mismatch = any(field in variant_like_fields for field in mismatched_fields)
    variant_missing = any(field in variant_like_fields for field in missing_fields)

    if matched_fields and not mismatched_fields and not missing_fields:
        decision = VerificationDecision.MATCH
        confidence = 0.90 if expected_variant_text else 0.86
    elif brand_mismatch:
        decision = VerificationDecision.MISMATCH
        confidence = 0.78
    elif product_name_mismatch and (matched_fields or overall_overlap > 0):
        decision = VerificationDecision.PARTIAL_MATCH
        confidence = 0.6 if matched_fields else 0.5
    elif variant_mismatch:
        decision = VerificationDecision.PARTIAL_MATCH
        confidence = 0.64
    elif variant_missing and matched_fields:
        decision = VerificationDecision.AMBIGUOUS
        confidence = 0.46
    elif matched_fields and missing_fields:
        decision = VerificationDecision.PARTIAL_MATCH
        confidence = 0.54
    else:
        decision = VerificationDecision.INSUFFICIENT_EVIDENCE
        confidence = 0.24

    return ProductVerificationResult(
        decision=decision,
        matched_fields=matched_fields,
        mismatched_fields=mismatched_fields,
        missing_fields=missing_fields,
        expected_variant_text=expected_variant_text,
        selected_variant_text=selected_variant_text,
        available_variant_options=available_variant_options,
        comparison_summary=comparison_summary,
        confidence=confidence,
        user_safe_summary=_build_user_summary(
            decision=decision,
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            missing_fields=missing_fields,
            comparison_summary=comparison_summary,
        ),
        notes=comparison_summary,
    )
