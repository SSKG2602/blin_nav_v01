from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Body, Response, status
from pydantic import BaseModel

from browser_runtime.automation import (
    AMAZON_CART_URL,
    AMAZON_HOME_URL,
    action_guard,
    attempt_checkout_entry,
    dismiss_common_interruptions,
    extract_cart_evidence,
    extract_product_detail_evidence,
    open_best_search_result,
    recover_to_stable_page,
    safe_goto,
    safe_page_url,
    submit_search_query,
)
from browser_runtime.driver import browser_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["actions"])


class NavigateToSearchResultsRequest(BaseModel):
    query: str | None = None
    merchant: str | None = None


class InspectProductPageRequest(BaseModel):
    page_type: str | None = None


class HandleErrorRecoveryRequest(BaseModel):
    error_type: str | None = None


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
    _log_action("inspect_product_page", session_id, page_type=payload.page_type)
    notes: list[str] = []
    try:
        page = browser_session_manager.get_page(session_id)
        notes.extend(dismiss_common_interruptions(page))

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
    payload: EmptyActionRequest = Body(default_factory=EmptyActionRequest),
) -> Response:
    _log_action("verify_product_variant", session_id)
    try:
        page = browser_session_manager.get_page(session_id)
        notes = dismiss_common_interruptions(page)
        evidence = extract_product_detail_evidence(page)
        logger.info(
            "product_variant_info %s",
            {"session_id": str(session_id), "notes": notes or None, **evidence},
        )
    except Exception as exc:
        logger.error("verify_product_variant failed for session %s: %s", session_id, exc)
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
        if current_url is None or ("cart" not in current_url.lower() and "checkout" not in current_url.lower()):
            if not safe_goto(page, AMAZON_CART_URL):
                notes.append("cart_navigation_before_checkout_failed")

        initiated, checkout_notes = attempt_checkout_entry(page)
        notes.extend(checkout_notes)
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
