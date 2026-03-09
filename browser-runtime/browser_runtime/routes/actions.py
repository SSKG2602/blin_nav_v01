from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Body, Response, status
from pydantic import BaseModel

from browser_runtime.automation import (
    AMAZON_CART_URL,
    AMAZON_HOME_URL,
    AMAZON_ORDERS_URL,
    add_current_product_to_cart,
    action_guard,
    attempt_cancel_latest_order,
    attempt_checkout_entry,
    dismiss_common_interruptions,
    extract_cart_evidence,
    extract_product_detail_evidence,
    open_best_search_result,
    recover_to_stable_page,
    remove_cart_item,
    safe_goto,
    safe_page_url,
    select_variant_option,
    submit_search_query,
    update_cart_item_quantity,
)
from browser_runtime.config import settings
from browser_runtime.driver import browser_session_manager
from browser_runtime.observation.models import RuntimeOrderCancellationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["actions"])


class NavigateToSearchResultsRequest(BaseModel):
    query: str | None = None
    merchant: str | None = None


class InspectProductPageRequest(BaseModel):
    page_type: str | None = None
    candidate_url: str | None = None
    candidate_title: str | None = None


class HandleErrorRecoveryRequest(BaseModel):
    error_type: str | None = None


class SelectVariantRequest(BaseModel):
    variant_hint: str | None = None
    size_hint: str | None = None
    color_hint: str | None = None


class RemoveCartItemRequest(BaseModel):
    item_id: str | None = None
    title: str | None = None


class UpdateCartQuantityRequest(BaseModel):
    item_id: str | None = None
    title: str | None = None
    quantity: int


class EmptyActionRequest(BaseModel):
    pass


def _accepted_response() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _log_action(action: str, session_id: UUID, **fields: str | None) -> None:
    payload = {"action": action, "session_id": str(session_id), **fields}
    logger.info("browser_runtime_action %s", payload)


@router.post("/{session_id}/actions/navigate_to_search_results", status_code=status.HTTP_204_NO_CONTENT)
def navigate_to_search_results(
    session_id: UUID,
    payload: NavigateToSearchResultsRequest = Body(default_factory=NavigateToSearchResultsRequest),
) -> Response:
    _log_action(
        "navigate_to_search_results",
        session_id,
        query=payload.query,
        merchant=payload.merchant,
    )
    page = browser_session_manager.get_page(session_id)
    notes: list[str] = []
    try:
        notes.extend(dismiss_common_interruptions(page))
        current_url = safe_page_url(page)

        if action_guard.should_skip_duplicate_search(
            session_id,
            query=payload.query,
            current_url=current_url,
        ):
            notes.append("duplicate_search_skipped")
            logger.info(
                "navigate_to_search_results_summary %s",
                {"session_id": str(session_id), "notes": notes},
            )
            return _accepted_response()

        if current_url is None or "amazon.in" not in current_url.lower():
            if not safe_goto(page, AMAZON_HOME_URL):
                notes.append("home_navigation_failed")

        submitted, submit_notes = submit_search_query(page, payload.query)
        notes.extend(submit_notes)
        if submitted:
            action_guard.record_search(
                session_id,
                query=payload.query,
                current_url=safe_page_url(page),
            )
    except Exception as exc:
        logger.error(
            "navigate_to_search_results failed for session %s: %s",
            session_id,
            exc,
        )
    logger.info(
        "navigate_to_search_results_summary %s",
        {"session_id": str(session_id), "notes": notes or None},
    )
    return _accepted_response()


@router.post("/{session_id}/actions/inspect_product_page", status_code=status.HTTP_204_NO_CONTENT)
def inspect_product_page(
    session_id: UUID,
    payload: InspectProductPageRequest = Body(default_factory=InspectProductPageRequest),
) -> Response:
    _log_action(
        "inspect_product_page",
        session_id,
        page_type=payload.page_type,
        candidate_url=payload.candidate_url,
        candidate_title=payload.candidate_title,
    )
    notes: list[str] = []
    try:
        page = browser_session_manager.get_page(session_id)
        notes.extend(dismiss_common_interruptions(page))
        candidate = None
        opened = False
        if payload.candidate_url:
            candidate = {
                "title": payload.candidate_title,
                "url": payload.candidate_url,
            }
            opened = safe_goto(page, payload.candidate_url)
            if not opened:
                notes.append("candidate_navigation_failed")
            else:
                action_guard.record_product_open(
                    session_id,
                    current_url=safe_page_url(page),
                )
        else:
            opened, candidate, selection_notes = open_best_search_result(page, session_id=session_id)
            notes.extend(selection_notes)
        evidence = extract_product_detail_evidence(page)
        if not opened:
            notes.append("product_open_not_confirmed")
        logger.info(
            "inspect_product_page_summary %s",
            {
                "session_id": str(session_id),
                "page_type": payload.page_type,
                "opened": opened,
                "selected_candidate": candidate,
                "evidence": evidence,
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("inspect_product_page failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/verify_product_variant", status_code=status.HTTP_204_NO_CONTENT)
def verify_product_variant(
    session_id: UUID,
    payload: SelectVariantRequest = Body(default_factory=SelectVariantRequest),
) -> Response:
    _log_action(
        "verify_product_variant",
        session_id,
        variant_hint=payload.variant_hint,
        size_hint=payload.size_hint,
        color_hint=payload.color_hint,
    )
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        selected, variant_notes, signature = select_variant_option(
            page,
            session_id=session_id,
            variant_hint=payload.variant_hint,
            size_hint=payload.size_hint,
            color_hint=payload.color_hint,
        )
        notes.extend(variant_notes)
        evidence = extract_product_detail_evidence(page)
        strong_boundary = bool(
            evidence.get("title")
            and (evidence.get("price_text") or evidence.get("availability_text"))
        )
        logger.info(
            "product_variant_info %s",
            {
                "session_id": str(session_id),
                "variant_selected": selected,
                "variant_signature": signature,
                "strong_boundary": strong_boundary,
                "notes": notes or None,
                **evidence,
            },
        )
    except Exception as exc:
        logger.error("verify_product_variant failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/select_variant", status_code=status.HTTP_204_NO_CONTENT)
def select_variant(
    session_id: UUID,
    payload: SelectVariantRequest = Body(default_factory=SelectVariantRequest),
) -> Response:
    _log_action(
        "select_variant",
        session_id,
        variant_hint=payload.variant_hint,
        size_hint=payload.size_hint,
        color_hint=payload.color_hint,
    )
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        selected, selection_notes, signature = select_variant_option(
            page,
            session_id=session_id,
            variant_hint=payload.variant_hint,
            size_hint=payload.size_hint,
            color_hint=payload.color_hint,
        )
        notes.extend(selection_notes)
        logger.info(
            "select_variant_summary %s",
            {
                "session_id": str(session_id),
                "selected": selected,
                "variant_signature": signature,
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("select_variant failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/add_to_cart", status_code=status.HTTP_204_NO_CONTENT)
def add_to_cart(
    session_id: UUID,
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> Response:
    _log_action("add_to_cart", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        added, add_notes = add_current_product_to_cart(page, session_id=session_id)
        notes.extend(add_notes)
        logger.info(
            "add_to_cart_summary %s",
            {
                "session_id": str(session_id),
                "added": added,
                "current_url": safe_page_url(page),
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("add_to_cart failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/review_cart", status_code=status.HTTP_204_NO_CONTENT)
def review_cart(
    session_id: UUID,
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> Response:
    _log_action("review_cart", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        current_url = safe_page_url(page)
        if current_url is None or "cart" not in current_url.lower():
            if not safe_goto(page, AMAZON_CART_URL):
                notes.append("cart_navigation_failed")
        cart_evidence = extract_cart_evidence(page)
        if cart_evidence.get("cart_item_count") in {0, None}:
            notes.append("cart_items_not_confirmed")
        if cart_evidence.get("checkout_ready") is None:
            notes.append("checkout_readiness_unclear")
        logger.info(
            "review_cart_summary %s",
            {
                "session_id": str(session_id),
                "cart_item_count": cart_evidence.get("cart_item_count"),
                "checkout_ready": cart_evidence.get("checkout_ready"),
                "notes": (notes + (cart_evidence.get("notes") or [])) or None,
            },
        )
    except Exception as exc:
        logger.error("review_cart failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/remove_cart_item", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item_action(
    session_id: UUID,
    payload: RemoveCartItemRequest = Body(default_factory=RemoveCartItemRequest),
) -> Response:
    _log_action("remove_cart_item", session_id, item_id=payload.item_id, title=payload.title)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        current_url = safe_page_url(page)
        if current_url is None or "cart" not in current_url.lower():
            if not safe_goto(page, AMAZON_CART_URL):
                notes.append("cart_navigation_before_remove_failed")

        removed, remove_notes = remove_cart_item(
            page,
            item_id=payload.item_id,
            title=payload.title,
        )
        notes.extend(remove_notes)
        cart_evidence = extract_cart_evidence(page)
        logger.info(
            "remove_cart_item_summary %s",
            {
                "session_id": str(session_id),
                "removed": removed,
                "cart_item_count": cart_evidence.get("cart_item_count"),
                "notes": (notes + (cart_evidence.get("notes") or [])) or None,
            },
        )
    except Exception as exc:
        logger.error("remove_cart_item failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/update_cart_quantity", status_code=status.HTTP_204_NO_CONTENT)
def update_cart_quantity_action(
    session_id: UUID,
    payload: UpdateCartQuantityRequest,
) -> Response:
    _log_action(
        "update_cart_quantity",
        session_id,
        item_id=payload.item_id,
        title=payload.title,
        quantity=str(payload.quantity),
    )
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        current_url = safe_page_url(page)
        if current_url is None or "cart" not in current_url.lower():
            if not safe_goto(page, AMAZON_CART_URL):
                notes.append("cart_navigation_before_quantity_failed")

        updated, update_notes = update_cart_item_quantity(
            page,
            item_id=payload.item_id,
            title=payload.title,
            quantity=payload.quantity,
        )
        notes.extend(update_notes)
        cart_evidence = extract_cart_evidence(page)
        logger.info(
            "update_cart_quantity_summary %s",
            {
                "session_id": str(session_id),
                "updated": updated,
                "cart_item_count": cart_evidence.get("cart_item_count"),
                "notes": (notes + (cart_evidence.get("notes") or [])) or None,
            },
        )
    except Exception as exc:
        logger.error("update_cart_quantity failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/perform_checkout", status_code=status.HTTP_204_NO_CONTENT)
def perform_checkout(
    session_id: UUID,
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> Response:
    _log_action("perform_checkout", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        current_url = safe_page_url(page)
        if action_guard.should_skip_duplicate_checkout_attempt(
            session_id,
            current_url=current_url,
        ):
            notes.append("duplicate_checkout_attempt_skipped")
            logger.info(
                "perform_checkout_initiated %s",
                {
                    "session_id": str(session_id),
                    "initiated": True,
                    "current_url": current_url,
                    "notes": notes or None,
                },
            )
            return _accepted_response()

        if current_url is None or ("cart" not in current_url.lower() and "checkout" not in current_url.lower()):
            if not safe_goto(page, AMAZON_CART_URL):
                notes.append("cart_navigation_before_checkout_failed")

        initiated, checkout_notes = attempt_checkout_entry(page)
        notes.extend(checkout_notes)
        if initiated:
            action_guard.record_checkout_attempt(
                session_id,
                current_url=safe_page_url(page),
            )
        logger.info(
            "perform_checkout_initiated %s",
            {
                "session_id": str(session_id),
                "initiated": initiated,
                "current_url": safe_page_url(page),
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("perform_checkout failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/finalize_purchase", status_code=status.HTTP_204_NO_CONTENT)
def finalize_purchase(
    session_id: UUID,
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> Response:
    _log_action("finalize_purchase", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        current_url = safe_page_url(page) or ""
        current_url_lower = current_url.lower()

        confirmation_visible = any(
            token in current_url_lower
            for token in ("order-confirmation", "thankyou", "order-details", "order")
        )
        if confirmation_visible:
            notes.append("order_confirmation_already_visible")
        elif not settings.ALLOW_FINAL_PURCHASE_AUTOMATION:
            notes.append("final_purchase_automation_disabled")
        else:
            clicked = False
            selectors = [
                'input[name="placeYourOrder1"]',
                '#submitOrderButtonId',
                '#placeYourOrder',
                '#bottomSubmitOrderButtonId',
                'button[name="placeYourOrder1"]',
                'input[aria-label*="Place your order"]',
                'button[aria-label*="Place your order"]',
            ]
            for selector in selectors:
                locator = getattr(page, "locator", None)
                if not callable(locator):
                    continue
                button = locator(selector)
                is_visible = getattr(button, "is_visible", None)
                if callable(is_visible) and not is_visible(timeout=1500):
                    continue
                click = getattr(button, "click", None)
                if not callable(click):
                    continue
                click(timeout=3000)
                wait_for_load_state = getattr(page, "wait_for_load_state", None)
                if callable(wait_for_load_state):
                    wait_for_load_state("domcontentloaded")
                clicked = True
                notes.append(f"final_purchase_clicked:{selector}")
                break
            if not clicked:
                notes.append("final_purchase_button_not_found")

        logger.info(
            "finalize_purchase_summary %s",
            {
                "session_id": str(session_id),
                "current_url": safe_page_url(page),
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("finalize_purchase failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post("/{session_id}/actions/navigate_orders_history", status_code=status.HTTP_204_NO_CONTENT)
def navigate_orders_history(
    session_id: UUID,
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> Response:
    _log_action("navigate_orders_history", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        if not safe_goto(page, AMAZON_ORDERS_URL):
            notes.append("orders_navigation_failed")
        logger.info(
            "navigate_orders_history_summary %s",
            {
                "session_id": str(session_id),
                "landed_url": safe_page_url(page),
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("navigate_orders_history failed for session %s: %s", session_id, exc)
    return _accepted_response()


@router.post(
    "/{session_id}/actions/cancel_latest_order",
    response_model=RuntimeOrderCancellationResult,
)
def cancel_latest_order(
    session_id: UUID,
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> RuntimeOrderCancellationResult:
    _log_action("cancel_latest_order", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        result = attempt_cancel_latest_order(page)
        existing_notes = str(result.get("notes") or "").strip()
        combined_notes = ", ".join(
            note for note in [", ".join(notes) if notes else None, existing_notes or None] if note
        )
        payload = {
            **result,
            "notes": combined_notes or None,
        }
        logger.info("cancel_latest_order_summary %s", {"session_id": str(session_id), **payload})
        return RuntimeOrderCancellationResult.model_validate(payload)
    except Exception as exc:
        logger.error("cancel_latest_order failed for session %s: %s", session_id, exc)
        return RuntimeOrderCancellationResult(
            cancelled=False,
            cancellable=False,
            spoken_summary="I could not determine whether the latest order can be cancelled right now.",
            notes=str(exc),
        )


@router.post("/{session_id}/actions/handle_error_recovery", status_code=status.HTTP_204_NO_CONTENT)
def handle_error_recovery(
    session_id: UUID,
    payload: HandleErrorRecoveryRequest = Body(default_factory=HandleErrorRecoveryRequest),
) -> Response:
    _log_action("handle_error_recovery", session_id, error_type=payload.error_type)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        error_type = (payload.error_type or "").lower()
        preferred = "home"
        if "cart" in error_type or "checkout" in error_type:
            preferred = "cart"
        elif "search" in error_type or "navigation" in error_type:
            preferred = "search"

        recovery = recover_to_stable_page(page, preferred=preferred)
        notes.extend(recovery.get("notes") or [])
        if recovery.get("success") is not True and preferred != "home":
            safe_goto(page, AMAZON_HOME_URL)
            notes.append("home_fallback_after_recovery")

        logger.info(
            "handle_error_recovery_applied %s",
            {
                "session_id": str(session_id),
                "error_type": payload.error_type,
                "strategy": recovery.get("target"),
                "success": recovery.get("success"),
                "landed_url": recovery.get("landed_url"),
                "notes": notes or None,
            },
        )
    except Exception as exc:
        logger.error("handle_error_recovery failed for session %s: %s", session_id, exc)
    return _accepted_response()
