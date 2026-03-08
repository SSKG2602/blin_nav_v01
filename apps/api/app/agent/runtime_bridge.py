from __future__ import annotations

from datetime import datetime
from typing import Any

from app.agent.state import (
    AgentState,
    CheckoutProgress,
    ClarificationNeeded,
    NavResult,
    PostPurchaseObserved,
    RecoveryTriggered,
    ReviewAnalysisResult,
    TrustCheckResult,
    VerificationResult,
)
from app.agent.product_verification import verify_product_against_intent
from app.schemas.cart_context import CartItemContext, CartSnapshot
from app.schemas.clarification import (
    ClarificationOption,
    ClarificationKind,
    ClarificationRequest,
    ClarificationStatus,
)
from app.schemas.control_state import RecoveryKind
from app.schemas.intent import InterpretedUserIntent
from app.schemas.multimodal_assessment import MultimodalAssessment
from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate
from app.schemas.product_verification import ProductIntentSpec, ProductVerificationResult, VerificationDecision
from app.schemas.purchase_support import FinalPurchaseConfirmation, PostPurchaseSummary
from app.schemas.review_analysis import ReviewAssessment, ReviewConflictLevel
from app.schemas.session_context import SessionContextSnapshot
from app.schemas.trust_verification import TrustAssessment


def _truthy_text(value: str | None) -> str | None:
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        if cleaned:
            return cleaned
    return None


def build_cart_snapshot(
    *,
    page: PageUnderstanding | None,
    observation: dict[str, Any] | None,
    previous_snapshot: CartSnapshot | None = None,
) -> CartSnapshot | None:
    if page is None and previous_snapshot is None and not isinstance(observation, dict):
        return None

    raw_items = observation.get("cart_items") if isinstance(observation, dict) else None
    items: list[CartItemContext] = []
    if isinstance(raw_items, list):
        for index, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                continue
            items.append(
                CartItemContext(
                    item_id=_truthy_text(raw.get("item_id")) or f"cart-item-{index}",
                    title=_truthy_text(raw.get("title")),
                    price_text=_truthy_text(raw.get("price_text")),
                    quantity_text=_truthy_text(raw.get("quantity_text")),
                    variant_text=_truthy_text(raw.get("variant_text")),
                    url=_truthy_text(raw.get("url")),
                    merchant_item_ref=_truthy_text(raw.get("merchant_item_ref")),
                    notes=_truthy_text(raw.get("notes")),
                )
            )

    if not items and previous_snapshot is not None:
        items = list(previous_snapshot.items)

    cart_item_count = page.cart_item_count if page is not None else None
    if cart_item_count is None and items:
        cart_item_count = len(items)

    checkout_ready = page.checkout_ready if page is not None else None
    notes = _truthy_text(page.notes if page is not None else None)
    return CartSnapshot(
        items=items,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
        currency_text=_truthy_text(observation.get("currency_text")) if isinstance(observation, dict) else None,
        notes=notes,
    )

def _describe_candidate_differences(
    *,
    candidate,
    baseline,
) -> str | None:
    differences: list[str] = []
    if candidate.brand_text and candidate.brand_text != baseline.brand_text:
        differences.append(f"brand {candidate.brand_text}")
    if candidate.variant_text and candidate.variant_text != baseline.variant_text:
        differences.append(f"variant {candidate.variant_text}")
    if candidate.price_text and candidate.price_text != baseline.price_text:
        differences.append(f"price {candidate.price_text}")
    if not differences and candidate.title and candidate.title != baseline.title:
        differences.append(candidate.title)
    if not differences:
        return None
    return ", ".join(differences[:3])


def _build_candidate_selection_request(
    *,
    current_state: AgentState,
    page: PageUnderstanding | None,
    product_intent: ProductIntentSpec | None,
) -> ClarificationRequest | None:
    if (
        current_state != AgentState.SEARCHING_PRODUCTS
        or page is None
        or page.page_type != PageType.SEARCH_RESULTS
        or product_intent is None
        or len(page.product_candidates) < 2
    ):
        return None

    scored: list[tuple[float, ProductCandidate, ClarificationOption, ProductVerificationResult]] = []
    for index, candidate in enumerate(page.product_candidates[:3]):
        verification = verify_product_against_intent(product_intent, candidate)
        decision_weight = {
            VerificationDecision.MATCH: 40,
            VerificationDecision.PARTIAL_MATCH: 28,
            VerificationDecision.AMBIGUOUS: 22,
            VerificationDecision.INSUFFICIENT_EVIDENCE: 12,
            VerificationDecision.MISMATCH: 0,
        }[verification.decision]
        option = ClarificationOption(
            label=f"Option {index + 1}",
            title=candidate.title or f"Candidate {index + 1}",
            price_text=candidate.price_text,
            variant_text=candidate.variant_text,
            candidate_url=candidate.url,
        )
        scored.append((decision_weight + verification.confidence * 10.0, candidate, option, verification))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_candidate, best_option, best_verification = scored[0]
    second_score, second_candidate, second_option, _second_verification = scored[1]

    if best_score <= 0:
        return None

    best_option.difference_summary = _describe_candidate_differences(
        candidate=best_candidate,
        baseline=second_candidate,
    )
    second_option.difference_summary = _describe_candidate_differences(
        candidate=second_candidate,
        baseline=best_candidate,
    )

    if best_score - second_score > 6 and best_verification.decision == VerificationDecision.MATCH:
        return None

    prompt = (
        "I found multiple similar products. Say yes to continue with option 1, "
        "or restate the detail that matters most."
    )
    summary = (
        f"Option 1: {best_option.title}"
        + (f" ({best_option.difference_summary})" if best_option.difference_summary else "")
        + ". "
        + f"Option 2: {second_option.title}"
        + (f" ({second_option.difference_summary})" if second_option.difference_summary else "")
        + "."
    )
    return ClarificationRequest(
        kind=ClarificationKind.PRODUCT_SELECTION,
        status=ClarificationStatus.PENDING,
        reason="Top search candidates are similar enough to require bounded confirmation.",
        prompt_to_user=prompt,
        original_user_goal=_truthy_text(product_intent.raw_query),
        candidate_summary=summary,
        candidate_options=[best_option, second_option],
        expected_fields=["brand", "size_text", "variant"],
        resume_state=AgentState.SEARCHING_PRODUCTS.value,
        created_at=datetime.utcnow(),
    )


def derive_clarification_request(
    *,
    current_state: AgentState,
    page: PageUnderstanding | None,
    derived_intent: InterpretedUserIntent | None,
    product_intent: ProductIntentSpec | None,
    verification: ProductVerificationResult | None,
    review_assessment: ReviewAssessment | None,
    previous_request: ClarificationRequest | None,
    interruption_active: bool = False,
) -> ClarificationRequest | None:
    if previous_request is not None and previous_request.status == ClarificationStatus.PENDING:
        return previous_request

    if interruption_active:
        return ClarificationRequest(
            kind=ClarificationKind.INTERRUPTION_REANCHOR,
            status=ClarificationStatus.PENDING,
            reason="The user interrupted the current action and the flow must be re-anchored safely.",
            prompt_to_user="I paused the current action. Say the next shopping step or approve resuming carefully.",
            original_user_goal=_truthy_text(
                product_intent.raw_query if product_intent is not None else None
            ),
            resume_state=current_state.value,
            created_at=datetime.utcnow(),
        )

    if derived_intent is not None and derived_intent.requires_clarification:
        expected_fields: list[str] = []
        if derived_intent.product_intent is None or not derived_intent.product_intent.product_name:
            expected_fields.append("product_name")
        return ClarificationRequest(
            kind=ClarificationKind.INTENT_COMPLETENESS,
            status=ClarificationStatus.PENDING,
            reason="The interpreted shopping intent is incomplete for safe action.",
            prompt_to_user="Please restate the product and key details before I continue.",
            original_user_goal=derived_intent.raw_utterance,
            expected_fields=expected_fields,
            resume_state=AgentState.SESSION_INITIALIZING.value,
            created_at=datetime.utcnow(),
        )

    candidate_selection_request = _build_candidate_selection_request(
        current_state=current_state,
        page=page,
        product_intent=product_intent,
    )
    if candidate_selection_request is not None:
        return candidate_selection_request

    if verification is None:
        return None

    if verification.decision == VerificationDecision.AMBIGUOUS:
        return ClarificationRequest(
            kind=ClarificationKind.PRODUCT_AMBIGUITY,
            status=ClarificationStatus.PENDING,
            reason=verification.notes or "Candidate product signals remain ambiguous.",
            prompt_to_user=verification.user_safe_summary,
            original_user_goal=_truthy_text(product_intent.raw_query if product_intent is not None else None),
            candidate_summary=verification.user_safe_summary,
            candidate_options=[],
            expected_fields=list(verification.missing_fields),
            resume_state=AgentState.VIEWING_PRODUCT_DETAIL.value,
            created_at=datetime.utcnow(),
        )

    if verification.decision == VerificationDecision.PARTIAL_MATCH:
        return ClarificationRequest(
            kind=ClarificationKind.PARTIAL_MATCH,
            status=ClarificationStatus.PENDING,
            reason="The current candidate only partially matches the requested product.",
            prompt_to_user=verification.user_safe_summary,
            original_user_goal=_truthy_text(product_intent.raw_query if product_intent is not None else None),
            candidate_summary=verification.user_safe_summary,
            candidate_options=[],
            expected_fields=list(verification.mismatched_fields or verification.missing_fields),
            resume_state=AgentState.VIEWING_PRODUCT_DETAIL.value,
            created_at=datetime.utcnow(),
        )

    if (
        verification.decision == VerificationDecision.MATCH
        and verification.missing_fields
        and any(field in {"variant", "size_text", "quantity_text", "color"} for field in verification.missing_fields)
    ):
        return ClarificationRequest(
            kind=ClarificationKind.VARIANT_PRECISION,
            status=ClarificationStatus.PENDING,
            reason="Variant precision is still unclear even though the base product appears matched.",
            prompt_to_user="Please confirm the exact variant or restate the missing size, quantity, or color.",
            original_user_goal=_truthy_text(product_intent.raw_query if product_intent is not None else None),
            candidate_summary=verification.comparison_summary or verification.user_safe_summary,
            candidate_options=[],
            expected_fields=list(verification.missing_fields),
            resume_state=AgentState.VIEWING_PRODUCT_DETAIL.value,
            created_at=datetime.utcnow(),
        )

    if (
        review_assessment is not None
        and review_assessment.conflict_level == ReviewConflictLevel.MEDIUM
        and current_state == AgentState.REVIEW_ANALYSIS
    ):
        return ClarificationRequest(
            kind=ClarificationKind.PRODUCT_SELECTION,
            status=ClarificationStatus.PENDING,
            reason="Review evidence is mixed and requires explicit bounded confirmation.",
            prompt_to_user=review_assessment.review_summary_spoken,
            original_user_goal=_truthy_text(product_intent.raw_query if product_intent is not None else None),
            candidate_summary=review_assessment.review_summary_spoken,
            candidate_options=[],
            resume_state=AgentState.REVIEW_ANALYSIS.value,
            created_at=datetime.utcnow(),
        )

    return None


def derive_runtime_follow_up_event(
    *,
    current_state: AgentState,
    page: PageUnderstanding | None,
    trust_assessment: TrustAssessment,
    review_assessment: ReviewAssessment,
    trust_query: str | None,
    trust_merchant: str | None,
    verification: ProductVerificationResult | None,
    clarification_request: ClarificationRequest | None,
    final_purchase_confirmation: FinalPurchaseConfirmation,
    post_purchase_summary: PostPurchaseSummary,
    low_confidence_status,
    recovery_status,
    cart_snapshot: CartSnapshot | None,
    consumed: set[str],
):
    if (
        clarification_request is not None
        and clarification_request.status == ClarificationStatus.PENDING
        and current_state != AgentState.CLARIFICATION_REQUIRED
        and "clarification" not in consumed
    ):
        consumed.add("clarification")
        return ClarificationNeeded(
            kind=clarification_request.kind,
            reason=clarification_request.reason,
            prompt_to_user=clarification_request.prompt_to_user,
            original_user_goal=clarification_request.original_user_goal,
            candidate_summary=clarification_request.candidate_summary,
            candidate_options=list(clarification_request.candidate_options),
            expected_fields=list(clarification_request.expected_fields),
            resume_state=clarification_request.resume_state,
        )

    if (
        low_confidence_status.active
        and current_state
        not in {
            AgentState.CLARIFICATION_REQUIRED,
            AgentState.CHECKPOINT_SENSITIVE_ACTION,
            AgentState.FINAL_CONFIRMATION,
            AgentState.LOW_CONFIDENCE_HALT,
            AgentState.SESSION_CLOSING,
            AgentState.DONE,
        }
        and "low_confidence" not in consumed
    ):
        consumed.add("low_confidence")
        return RecoveryTriggered(reason=low_confidence_status.reason or "low_confidence")

    if current_state == AgentState.TRUST_CHECK and "trust_check" not in consumed:
        consumed.add("trust_check")
        return TrustCheckResult(
            status=trust_assessment.status,
            reason=trust_assessment.reasoning_summary,
            query=trust_query,
            merchant=trust_merchant,
        )

    if (
        current_state == AgentState.SEARCHING_PRODUCTS
        and page is not None
        and page.page_type in {PageType.SEARCH_RESULTS, PageType.PRODUCT_DETAIL}
        and page.confidence >= 0.50
        and "nav_result" not in consumed
    ):
        consumed.add("nav_result")
        return NavResult(
            success=True,
            page_type=page.page_type.value.lower(),
            confidence=page.confidence,
        )

    if current_state == AgentState.VIEWING_PRODUCT_DETAIL and verification is not None and "verification" not in consumed:
        consumed.add("verification")
        if verification.decision == VerificationDecision.MATCH:
            return VerificationResult(success=True, low_confidence=False, notes=verification.user_safe_summary)
        return VerificationResult(
            success=False,
            low_confidence=verification.decision == VerificationDecision.INSUFFICIENT_EVIDENCE,
            notes=verification.user_safe_summary,
        )

    if current_state == AgentState.REVIEW_ANALYSIS and "review" not in consumed:
        consumed.add("review")
        return ReviewAnalysisResult(
            conflict_level=review_assessment.conflict_level,
            requires_user_confirmation=review_assessment.conflict_level
            in {ReviewConflictLevel.MEDIUM, ReviewConflictLevel.HIGH},
            notes=review_assessment.review_summary_spoken,
        )

    if current_state == AgentState.CART_VERIFICATION and "cart_progress" not in consumed:
        if cart_snapshot is not None and (cart_snapshot.cart_item_count or 0) > 0:
            consumed.add("cart_progress")
            return CheckoutProgress(
                proceed_to_checkout=cart_snapshot.checkout_ready is True,
                sensitive_step_required=False,
                completed=False,
                low_confidence=False,
            )

    if current_state in {AgentState.CHECKOUT_FLOW, AgentState.ASSISTED_MODE} and "checkout_progress" not in consumed:
        if page is not None and page.page_type == PageType.CHECKOUT:
            consumed.add("checkout_progress")
            if final_purchase_confirmation.required and not final_purchase_confirmation.confirmed:
                return CheckoutProgress(
                    proceed_to_checkout=True,
                    sensitive_step_required=False,
                    completed=True,
                    low_confidence=False,
                )
            return CheckoutProgress(
                proceed_to_checkout=True,
                sensitive_step_required=False,
                completed=False,
                low_confidence=False,
            )

    if (
        current_state == AgentState.ORDER_PLACED
        and "post_purchase" not in consumed
        and (
            _truthy_text(post_purchase_summary.order_item_title)
            or "order appears placed" in (post_purchase_summary.spoken_summary or "").lower()
            or "order confirmation appears" in (post_purchase_summary.spoken_summary or "").lower()
        )
    ):
        consumed.add("post_purchase")
        return PostPurchaseObserved(
            detected=True,
            notes=post_purchase_summary.notes,
        )

    if (
        recovery_status.active
        and recovery_status.recovery_kind
        in {
            RecoveryKind.MODAL_INTERRUPTION,
            RecoveryKind.CHECKOUT_BLOCKED,
            RecoveryKind.NAVIGATION_RECOVERY,
            RecoveryKind.PAGE_DESYNC,
        }
        and current_state
        in {
            AgentState.SEARCHING_PRODUCTS,
            AgentState.VIEWING_PRODUCT_DETAIL,
            AgentState.CART_VERIFICATION,
            AgentState.CHECKOUT_FLOW,
            AgentState.ASSISTED_MODE,
            AgentState.UI_STABILIZING,
        }
        and "recovery" not in consumed
    ):
        consumed.add("recovery")
        return RecoveryTriggered(
            reason=recovery_status.reason or recovery_status.last_attempt_summary
        )

    return None
