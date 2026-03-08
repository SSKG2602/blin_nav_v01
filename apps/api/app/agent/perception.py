from __future__ import annotations

from typing import Any

from app.schemas.page_understanding import PageType, PageUnderstanding, ProductCandidate


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = _normalize_text(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None

    text = _normalize_text(value)
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _to_page_type(value: Any) -> PageType | None:
    text = _normalize_text(value).replace("-", "_").replace(" ", "_")
    mapping = {
        "home": PageType.HOME,
        "search_results": PageType.SEARCH_RESULTS,
        "search": PageType.SEARCH_RESULTS,
        "results": PageType.SEARCH_RESULTS,
        "product_detail": PageType.PRODUCT_DETAIL,
        "product": PageType.PRODUCT_DETAIL,
        "pdp": PageType.PRODUCT_DETAIL,
        "cart": PageType.CART,
        "basket": PageType.CART,
        "checkout": PageType.CHECKOUT,
        "unknown": PageType.UNKNOWN,
    }
    return mapping.get(text)


def _coerce_candidate(value: Any) -> ProductCandidate | None:
    if isinstance(value, ProductCandidate):
        return value
    if isinstance(value, dict):
        return ProductCandidate.model_validate(value)
    return None


def _extract_candidates(raw_data: dict[str, Any]) -> list[ProductCandidate]:
    source = raw_data.get("product_candidates")
    if source is None:
        source = raw_data.get("results")
    if source is None:
        source = raw_data.get("items")

    candidates: list[ProductCandidate] = []
    if isinstance(source, list):
        for item in source:
            candidate = _coerce_candidate(item)
            if candidate is not None:
                candidates.append(candidate)
    elif source is not None:
        candidate = _coerce_candidate(source)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _build_detail_candidate(raw_data: dict[str, Any]) -> ProductCandidate | None:
    payload = {
        "title": raw_data.get("product_title") or raw_data.get("title"),
        "price_text": raw_data.get("price_text") or raw_data.get("price"),
        "url": raw_data.get("url"),
        "rating_text": raw_data.get("rating_text"),
        "review_count_text": raw_data.get("review_count_text"),
        "availability_text": raw_data.get("availability_text"),
        "variant_text": raw_data.get("variant_text"),
        "brand_text": raw_data.get("brand_text"),
        "review_snippets": raw_data.get("review_snippets") or [],
        "variant_options": raw_data.get("variant_options") or [],
    }
    if any(
        payload.get(field)
        for field in (
            "title",
            "price_text",
            "url",
            "rating_text",
            "review_count_text",
            "availability_text",
            "variant_text",
            "brand_text",
        )
    ) or payload["review_snippets"] or payload["variant_options"]:
        return ProductCandidate.model_validate(payload)
    return None


def _infer_page_type(
    raw_data: dict[str, Any],
    *,
    explicit_page_type: PageType | None,
    candidates: list[ProductCandidate],
    primary_product: ProductCandidate | None,
    cart_item_count: int | None,
    checkout_ready: bool | None,
    page_title: str | None,
) -> PageType:
    if explicit_page_type is not None:
        return explicit_page_type

    url_text = _normalize_text(raw_data.get("url"))
    title_text = _normalize_text(page_title)

    if checkout_ready is True or raw_data.get("is_checkout") is True:
        return PageType.CHECKOUT
    if "checkout" in url_text or "checkout" in title_text:
        return PageType.CHECKOUT

    if cart_item_count is not None or raw_data.get("is_cart") is True:
        return PageType.CART
    if "cart" in url_text or "cart" in title_text:
        return PageType.CART

    if raw_data.get("is_product_detail") is True:
        return PageType.PRODUCT_DETAIL
    if primary_product is not None and ("dp/" in url_text or "product" in title_text):
        return PageType.PRODUCT_DETAIL

    if candidates:
        return PageType.SEARCH_RESULTS
    if raw_data.get("is_home") is True:
        return PageType.HOME
    if "amazon.in" in url_text and "/s?" not in url_text and "cart" not in url_text:
        return PageType.HOME

    return PageType.UNKNOWN


def _estimate_confidence(
    page_type: PageType,
    *,
    explicit_page_type: PageType | None,
    candidates_count: int,
    has_primary: bool,
    cart_item_count: int | None,
    checkout_ready: bool | None,
) -> float:
    base_by_type = {
        PageType.HOME: 0.50,
        PageType.SEARCH_RESULTS: 0.60,
        PageType.PRODUCT_DETAIL: 0.62,
        PageType.CART: 0.65,
        PageType.CHECKOUT: 0.65,
        PageType.UNKNOWN: 0.25,
    }
    confidence = base_by_type[page_type]

    if explicit_page_type is not None:
        confidence += 0.10
    if candidates_count > 0:
        confidence += min(0.15, 0.03 * candidates_count)
    if has_primary:
        confidence += 0.08
    if page_type == PageType.CART and cart_item_count is not None:
        confidence += 0.08
    if page_type == PageType.CHECKOUT and checkout_ready is not None:
        confidence += 0.08

    return max(0.0, min(0.95, confidence))


def classify_page_understanding(raw_data: dict[str, Any]) -> PageUnderstanding:
    page_title_value = raw_data.get("page_title")
    page_title = str(page_title_value).strip() if isinstance(page_title_value, str) else None

    explicit_page_type = _to_page_type(raw_data.get("page_type"))
    candidates = _extract_candidates(raw_data)

    primary_product = _coerce_candidate(raw_data.get("primary_product"))
    if primary_product is None:
        detail_candidate = _build_detail_candidate(raw_data)
        if detail_candidate is not None:
            primary_product = detail_candidate
    if primary_product is None and candidates:
        primary_product = candidates[0]

    cart_item_count = _coerce_int(raw_data.get("cart_item_count"))
    checkout_ready = _coerce_bool(raw_data.get("checkout_ready"))

    page_type = _infer_page_type(
        raw_data,
        explicit_page_type=explicit_page_type,
        candidates=candidates,
        primary_product=primary_product,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
        page_title=page_title,
    )
    confidence = _estimate_confidence(
        page_type,
        explicit_page_type=explicit_page_type,
        candidates_count=len(candidates),
        has_primary=primary_product is not None,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
    )

    notes = raw_data.get("notes") if isinstance(raw_data.get("notes"), str) else None
    if notes is None and page_type == PageType.UNKNOWN:
        notes = "Page type could not be inferred from current signals."

    return PageUnderstanding(
        page_type=page_type,
        page_title=page_title,
        product_candidates=candidates,
        primary_product=primary_product,
        cart_item_count=cart_item_count,
        checkout_ready=checkout_ready,
        confidence=confidence,
        notes=notes,
    )
