from __future__ import annotations

import re

from app.schemas.page_understanding import ProductCandidate
from app.schemas.product_verification import (
    ProductIntentSpec,
    ProductVerificationResult,
    VerificationDecision,
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_phrase(expected: str, observed: str) -> bool:
    expected_norm = _normalize_text(expected)
    observed_norm = _normalize_text(observed)
    if not expected_norm or not observed_norm:
        return False
    return expected_norm in observed_norm


def _token_overlap_ratio(query: str, observed: str) -> float:
    query_tokens = {token for token in _normalize_text(query).split() if token}
    observed_tokens = {token for token in _normalize_text(observed).split() if token}
    if not query_tokens or not observed_tokens:
        return 0.0
    overlap = query_tokens.intersection(observed_tokens)
    return len(overlap) / len(query_tokens)


def _build_user_summary(
    *,
    decision: VerificationDecision,
    matched_fields: list[str],
    mismatched_fields: list[str],
    missing_fields: list[str],
) -> str:
    if decision == VerificationDecision.MATCH:
        return "This product appears to match your request."
    if decision == VerificationDecision.PARTIAL_MATCH:
        return (
            "This is a partial match. "
            f"Matched fields: {', '.join(matched_fields) or 'none'}. "
            f"Mismatches: {', '.join(mismatched_fields) or 'none'}."
        )
    if decision == VerificationDecision.MISMATCH:
        return (
            "This product does not match your request. "
            f"Mismatched fields: {', '.join(mismatched_fields) or 'unspecified'}."
        )
    if decision == VerificationDecision.AMBIGUOUS:
        return (
            "I found a possible product, but key variant details are unclear. "
            f"Please confirm: {', '.join(missing_fields) or 'variant details'}."
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
            ),
            notes="No product candidate was available for comparison.",
        )

    observed_text = " ".join(
        part
        for part in [
            candidate.title,
            candidate.variant_text,
            candidate.availability_text,
            candidate.price_text,
        ]
        if part
    )
    observed_norm = _normalize_text(observed_text)
    if not observed_norm:
        missing = list(requested_fields.keys()) or ["raw_query"]
        return ProductVerificationResult(
            decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
            matched_fields=[],
            mismatched_fields=[],
            missing_fields=missing,
            confidence=0.20,
            user_safe_summary=_build_user_summary(
                decision=VerificationDecision.INSUFFICIENT_EVIDENCE,
                matched_fields=[],
                mismatched_fields=[],
                missing_fields=missing,
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
                confidence=0.60,
                user_safe_summary=_build_user_summary(
                    decision=VerificationDecision.PARTIAL_MATCH,
                    matched_fields=["raw_query"],
                    mismatched_fields=[],
                    missing_fields=[],
                ),
                notes="Only raw query was available; using token overlap.",
            )
        if overlap_ratio > 0.0:
            return ProductVerificationResult(
                decision=VerificationDecision.AMBIGUOUS,
                matched_fields=[],
                mismatched_fields=[],
                missing_fields=["raw_query"],
                confidence=0.35,
                user_safe_summary=_build_user_summary(
                    decision=VerificationDecision.AMBIGUOUS,
                    matched_fields=[],
                    mismatched_fields=[],
                    missing_fields=["raw_query"],
                ),
                notes="Raw query partially overlaps with candidate text.",
            )
        return ProductVerificationResult(
            decision=VerificationDecision.MISMATCH,
            matched_fields=[],
            mismatched_fields=["raw_query"],
            missing_fields=[],
            confidence=0.70,
            user_safe_summary=_build_user_summary(
                decision=VerificationDecision.MISMATCH,
                matched_fields=[],
                mismatched_fields=["raw_query"],
                missing_fields=[],
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

        if field_name in {"brand", "product_name"} and candidate.title:
            mismatched_fields.append(field_name)
        else:
            missing_fields.append(field_name)

    variant_like_fields = {"variant", "size_text", "quantity_text", "color"}

    if matched_fields and not mismatched_fields and not missing_fields:
        decision = VerificationDecision.MATCH
        confidence = 0.88
    elif mismatched_fields and matched_fields:
        decision = VerificationDecision.PARTIAL_MATCH
        confidence = 0.58
    elif mismatched_fields and not matched_fields:
        decision = VerificationDecision.MISMATCH
        confidence = 0.76
    elif missing_fields and any(field in variant_like_fields for field in missing_fields):
        decision = VerificationDecision.AMBIGUOUS
        confidence = 0.42
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
        confidence=confidence,
        user_safe_summary=_build_user_summary(
            decision=decision,
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            missing_fields=missing_fields,
        ),
        notes=None,
    )

