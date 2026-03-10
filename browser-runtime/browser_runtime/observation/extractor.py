from __future__ import annotations

import base64
from typing import Any

from browser_runtime.automation import (
    classify_page_state,
    collect_semantic_page_signals,
    collect_search_result_candidates,
    detect_location_blocked,
    detect_checkout_entry_readiness,
    extract_cart_evidence,
    extract_latest_order_evidence,
    extract_product_detail_evidence,
    infer_page_hints,
    safe_page_title,
    safe_page_url,
)
from browser_runtime.observation.models import (
    RuntimePageObservation,
    RuntimeProductCandidate,
    RuntimeScreenshotObservation,
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = "".join(ch for ch in _normalize_text(value) if ch.isdigit())
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = _normalize_text(value).lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _coerce_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    candidate = RuntimeProductCandidate.model_validate(raw)
    return candidate.model_dump(exclude_none=True)


def _build_primary_from_detail(detail: dict[str, Any]) -> dict[str, Any] | None:
    primary = RuntimeProductCandidate(
        title=detail.get("title"),
        price_text=detail.get("price_text"),
        url=detail.get("url"),
        rating_text=detail.get("rating_text"),
        review_count_text=detail.get("review_count_text"),
        availability_text=detail.get("availability_text"),
        variant_text=detail.get("variant_text"),
        brand_text=detail.get("brand_text"),
        review_snippets=detail.get("review_snippets") or [],
        variant_options=detail.get("variant_options") or [],
    ).model_dump(exclude_none=True)
    meaningful_fields = {
        "title",
        "price_text",
        "url",
        "rating_text",
        "review_count_text",
        "availability_text",
        "variant_text",
        "brand_text",
    }
    if not any(_normalize_text(primary.get(field)) for field in meaningful_fields):
        if not primary.get("review_snippets") and not primary.get("variant_options"):
            return None
    return primary or None


def extract_observation_from_snapshot(snapshot: dict[str, Any]) -> RuntimePageObservation:
    observed_url = _normalize_text(snapshot.get("observed_url")) or None
    page_title = _normalize_text(snapshot.get("page_title")) or None

    candidates: list[dict[str, Any]] = []
    raw_candidates = snapshot.get("product_candidates")
    if isinstance(raw_candidates, list):
        for raw in raw_candidates:
            if isinstance(raw, dict):
                candidates.append(_coerce_candidate(raw))

    primary_product: dict[str, Any] | None = None
    raw_primary = snapshot.get("primary_product")
    if isinstance(raw_primary, dict):
        primary_product = _coerce_candidate(raw_primary)

    cart_item_count = _to_int(snapshot.get("cart_item_count"))
    checkout_ready = _to_bool(snapshot.get("checkout_ready"))
    cart_items = [
        item
        for item in (snapshot.get("cart_items") or [])
        if isinstance(item, dict)
    ] if isinstance(snapshot.get("cart_items"), list) else []

    raw_hints = snapshot.get("detected_page_hints")
    detected_page_hints: list[str] = []
    if isinstance(raw_hints, list):
        for raw in raw_hints:
            hint = _normalize_text(raw).lower().replace(" ", "_")
            if hint:
                detected_page_hints.append(hint)

    if not detected_page_hints:
        detected_page_hints = infer_page_hints(
            observed_url=observed_url,
            page_title=page_title,
            product_candidates=candidates,
            primary_product=primary_product,
            cart_item_count=cart_item_count,
            checkout_ready=checkout_ready,
        )

    notes = _normalize_text(snapshot.get("notes")) or None
    if notes is None and detected_page_hints == ["unknown"]:
        notes = "Could not extract strong page evidence."

    return RuntimePageObservation(
        observed_url=observed_url,
        page_title=page_title,
        detected_page_hints=detected_page_hints,
        product_candidates=candidates,
        primary_product=primary_product,
        cart_items=cart_items,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
        order_id_hint=_normalize_text(snapshot.get("order_id_hint")) or None,
        order_date_text=_normalize_text(snapshot.get("order_date_text")) or None,
        shipping_stage_text=_normalize_text(snapshot.get("shipping_stage_text")) or None,
        expected_delivery_text=_normalize_text(snapshot.get("expected_delivery_text")) or None,
        order_total_text=_normalize_text(snapshot.get("order_total_text")) or None,
        order_card_title=_normalize_text(snapshot.get("order_card_title")) or None,
        orders_page_url=_normalize_text(snapshot.get("orders_page_url")) or None,
        support_entry_hint=_normalize_text(snapshot.get("support_entry_hint")) or None,
        returns_entry_hint=_normalize_text(snapshot.get("returns_entry_hint")) or None,
        notes=notes,
    )


def extract_current_page_observation(page: Any) -> RuntimePageObservation:
    observed_url = safe_page_url(page)
    page_title = safe_page_title(page)
    page_state = classify_page_state(page)

    if detect_location_blocked(page):
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=["location_blocked", page_state],
            notes="Waiting for location selection.",
        )

    if page_state == "login":
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=["login"],
            notes="Sign-in required.",
        )

    if page_state == "blank":
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=["navigating"],
            notes="Navigation in progress.",
        )

    if page_state == "home":
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=["home"],
        )

    if page_state == "search_results":
        product_candidates = [
            candidate
            for candidate in collect_search_result_candidates(page, limit=3)
            if candidate
        ]
        hints = infer_page_hints(
            observed_url=observed_url,
            page_title=page_title,
            product_candidates=product_candidates,
            primary_product=None,
            cart_item_count=None,
            checkout_ready=None,
        )
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=hints or ["search_results"],
            product_candidates=product_candidates,
        )

    if page_state == "product":
        detail_evidence = extract_product_detail_evidence(page)
        primary_product = _build_primary_from_detail(detail_evidence)
        cart_evidence = extract_cart_evidence(page)
        cart_item_count = cart_evidence.get("cart_item_count")
        checkout_ready = cart_evidence.get("checkout_ready")
        notes_list: list[str] = []
        detail_notes = _normalize_text(detail_evidence.get("notes"))
        if detail_notes:
            notes_list.append(detail_notes)
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=["product_detail"],
            primary_product=primary_product,
            cart_item_count=cart_item_count,
            checkout_ready=checkout_ready,
            notes=", ".join(notes_list) if notes_list else None,
        )

    if page_state in {"cart", "checkout"}:
        cart_evidence = extract_cart_evidence(page)
        cart_items = [
            item
            for item in (cart_evidence.get("cart_items") or [])
            if isinstance(item, dict)
        ]
        checkout_ready = cart_evidence.get("checkout_ready")
        if checkout_ready is None:
            checkout_ready, _ = detect_checkout_entry_readiness(page)
        return RuntimePageObservation(
            observed_url=observed_url,
            page_title=page_title,
            detected_page_hints=[page_state],
            cart_items=cart_items,
            cart_item_count=cart_evidence.get("cart_item_count"),
            checkout_ready=checkout_ready,
            notes=", ".join(_normalize_text(item) for item in (cart_evidence.get("notes") or []) if _normalize_text(item)) or None,
        )

    product_candidates = collect_search_result_candidates(page, limit=5)
    product_candidates = [candidate for candidate in product_candidates if candidate]
    detail_evidence = extract_product_detail_evidence(page)
    primary_product = _build_primary_from_detail(detail_evidence)
    cart_evidence = extract_cart_evidence(page)
    orders_evidence = extract_latest_order_evidence(page)
    cart_item_count = cart_evidence.get("cart_item_count")
    checkout_ready = cart_evidence.get("checkout_ready")
    cart_items = [
        item
        for item in (cart_evidence.get("cart_items") or [])
        if isinstance(item, dict)
    ]
    if checkout_ready is None:
        checkout_ready, _ = detect_checkout_entry_readiness(page)

    notes_list: list[str] = []
    notes_list.extend(collect_semantic_page_signals(page))
    detail_notes = _normalize_text(detail_evidence.get("notes"))
    if detail_notes:
        notes_list.append(detail_notes)
    for item in cart_evidence.get("notes") or []:
        text = _normalize_text(item)
        if text:
            notes_list.append(text)

    hints = infer_page_hints(
        observed_url=observed_url,
        page_title=page_title,
        product_candidates=product_candidates,
        primary_product=primary_product,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
    )

    combined_identity = f"{_normalize_text(observed_url).lower()} {_normalize_text(page_title).lower()}"
    if any(token in combined_identity for token in ("thank you", "order placed", "order confirmation")):
        notes_list.append("order_confirmation_detected")

    if hints == ["unknown"]:
        notes_list.append("weak_page_evidence")

    return RuntimePageObservation(
        observed_url=observed_url,
        page_title=page_title,
        detected_page_hints=hints,
        product_candidates=product_candidates,
        primary_product=primary_product,
        cart_items=cart_items,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
        order_id_hint=_normalize_text(orders_evidence.get("order_id_hint")) or None,
        order_date_text=_normalize_text(orders_evidence.get("order_date_text")) or None,
        shipping_stage_text=_normalize_text(orders_evidence.get("shipping_stage_text")) or None,
        expected_delivery_text=_normalize_text(orders_evidence.get("expected_delivery_text")) or None,
        order_total_text=_normalize_text(orders_evidence.get("order_total_text")) or None,
        order_card_title=_normalize_text(orders_evidence.get("order_card_title")) or None,
        orders_page_url=_normalize_text(orders_evidence.get("orders_page_url")) or None,
        support_entry_hint=_normalize_text(orders_evidence.get("support_entry_hint")) or None,
        returns_entry_hint=_normalize_text(orders_evidence.get("returns_entry_hint")) or None,
        notes=", ".join(notes_list) if notes_list else None,
    )


def extract_current_page_screenshot(page: Any) -> RuntimeScreenshotObservation:
    screenshot_fn = getattr(page, "screenshot", None)
    if not callable(screenshot_fn):
        return RuntimeScreenshotObservation(
            image_base64=None,
            notes="Screenshot API unavailable on current page adapter.",
        )

    try:
        raw = screenshot_fn(type="png", full_page=True)
    except Exception as exc:
        return RuntimeScreenshotObservation(
            image_base64=None,
            notes=f"Screenshot capture failed: {exc}",
        )

    if isinstance(raw, bytes):
        encoded = base64.b64encode(raw).decode("ascii")
        return RuntimeScreenshotObservation(
            image_base64=encoded,
            notes=None if encoded else "Screenshot was empty.",
        )

    return RuntimeScreenshotObservation(
        image_base64=None,
        notes="Screenshot returned non-bytes payload.",
    )
