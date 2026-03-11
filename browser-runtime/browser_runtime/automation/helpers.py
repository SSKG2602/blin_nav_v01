from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse
from uuid import UUID

logger = logging.getLogger(__name__)

BB_HOME_URL = "https://demo.nopcommerce.com"
BB_CART_URL = "https://demo.nopcommerce.com/cart"
BB_ORDERS_URL = "https://demo.nopcommerce.com/customer/orders"

SEARCH_INPUT_SELECTORS = [
    "#small-searchterms",
    ".search-box-text",
    "input[name='q']",
    "#q",
    "input[type='search']",
]

SEARCH_SUBMIT_SELECTORS = [
    "button.search-box-button",
    "input.button-1.search-box-button",
    "form[action*='/search'] button[type='submit']",
    "form[action*='/search'] input[type='submit']",
    "button[type='submit']",
    "input[type='submit']",
]

SEARCH_PAGE_ANCHOR_SELECTORS = [
    ".search-page",
    "form[action*='/search']",
    "label[for='q']",
    "input[name='q']",
]

SEARCH_RESULT_CONTAINER_SELECTORS = [
    ".search-results .item-box",
    ".item-grid .item-box",
    ".product-grid .item-box",
    ".product-list .item-box",
    ".category-page .item-box",
    ".manufacturer-page .item-box",
]

SEARCH_RESULT_LINK_SELECTORS = [
    ".product-title a",
    "h2.product-title a",
    ".details a[href]",
    ".product-item a[href]",
]

CHECKOUT_BUTTON_SELECTORS = [
    "#checkout",
    "input[name='checkout']",
    "button[name='checkout']",
    ".checkout-button",
    "button:has-text('Checkout')",
    "input[value*='Checkout']",
    "a[href*='checkout']",
]

ADD_TO_CART_BUTTON_SELECTORS = [
    "button[id^='add-to-cart-button-']",
    "input[id^='add-to-cart-button-']",
    ".add-to-cart-button",
    ".product-essential .button-1",
    "button:has-text('Add to cart')",
    "input[value*='Add to cart']",
]

VARIANT_OPTION_SELECTORS = [
    "select[id^='product_attribute_']",
    ".attributes select",
    ".attributes .option-list label",
    "input[id^='product_attribute_'] + label",
    "label[for^='product_attribute_']",
]

CART_ROW_SELECTORS = [
    "tr.cart-item-row",
    ".shopping-cart-page table.cart tbody tr",
    ".order-summary-content table.cart tbody tr",
]

CART_REMOVE_SELECTORS = [
    "input[name='removefromcart']",
    ".remove-from-cart input[type='checkbox']",
    ".remove-from-cart button",
    ".remove-btn",
]

CART_UPDATE_SELECTORS = [
    "input[name='updatecart']",
    "button[name='updatecart']",
    ".update-cart-button",
]

CART_QUANTITY_SELECTORS = [
    "input.qty-input",
    "input[name*='itemquantity']",
    "input[name*='EnteredQuantity']",
    "select.qty-input",
]

ORDERS_CARD_SELECTORS = [
    ".order-list .order-item",
    ".order-list .section",
    ".order-details-page .page-body",
    ".order-overview",
]

ORDER_CANCEL_ENTRY_SELECTORS = [
    "button[class*='Cancel']",
    "a[href*='cancel']",
    "button[qa*='cancel']",
    "text=Cancel items",
    "text=Cancel order",
]

ORDER_CANCEL_CONFIRM_SELECTORS = [
    "button[class*='Confirm']",
    "button[qa*='confirm']",
    "button[class*='CancelSelected']",
    "text=Confirm cancellation",
    "text=Cancel selected items",
]

CAPTCHA_SELECTORS = [
    "input[name*='captcha']",
    "input[id*='captcha']",
    "img[src*='captcha']",
    "form[action*='captcha']",
]

OTP_SELECTORS = [
    "input[name*='otp']",
    "input[id*='otp']",
    "input[autocomplete='one-time-code']",
]

PAYMENT_AUTH_SELECTORS = [
    "input[name*='cvv']",
    "input[id*='cvv']",
    "input[name*='upi']",
    "iframe[name*='payment']",
]

PRODUCT_ANCHOR_SELECTORS = [
    "div.product-essential",
    "div.overview",
    "div.product-name h1",
    "button[id^='add-to-cart-button-']",
    ".attributes",
]

CART_ANCHOR_SELECTORS = [
    ".shopping-cart-page",
    ".order-summary-content",
    "table.cart",
    "#checkout",
]

CHECKOUT_ANCHOR_SELECTORS = [
    "#checkout",
    ".checkout-data",
    ".checkout-page",
    ".checkout-as-guest-button",
    "a[href*='checkout']",
]

MODAL_DISMISS_SELECTORS = [
    "button[aria-label='Close']",
    "button[class*='Close']",
    "button[class*='close']",
    "div[class*='Modal'] button",
    "button[class*='Dismiss']",
]

BB_LOCATION_MODAL_SELECTORS = [
    "div[class*='LocationModal']",
    "div[class*='DeliveryModal']",
    "div[class*='PincodeModal']",
    "button[class*='SelectCity']",
    "div[qa='location-modal']",
    "input[placeholder*='pincode']",
    "input[placeholder*='Pincode']",
]

BB_QUANTITY_STEPPER_SELECTORS = [
    "#topcartlink .cart-qty",
    ".cart-qty",
    ".bar-notification.success",
    "#bar-notification .content",
    "input.qty-input",
]

PRODUCT_TITLE_SELECTORS = [
    "div.product-name h1",
    "h1[itemprop='name']",
    "div.product-essential h1",
    "h1",
]

PRODUCT_PRICE_SELECTORS = [
    ".product-price span",
    ".prices .actual-price",
    ".prices .price.actual-price",
    "span[class*='price-value']",
    ".product-price",
]

SEARCH_RESULT_TITLE_SELECTORS = [
    ".product-title a",
    "h2.product-title a",
    ".product-title",
]

SEARCH_RESULT_SUMMARY_SELECTORS = [
    ".description",
    ".short-description",
]

SEARCH_RESULT_PRICE_SELECTORS = [
    ".prices .actual-price",
    ".prices .price.actual-price",
    ".prices span",
    ".product-price",
    ".price",
]

PRODUCT_AVAILABILITY_SELECTORS = [
    ".availability .value",
    ".stock .value",
    ".availability",
    ".stock",
    "button[id^='add-to-cart-button-']",
    ".add-to-cart-button",
]

PRODUCT_VARIANT_VALUE_SELECTORS = [
    "select[id^='product_attribute_'] option[selected]",
    "select[id^='product_attribute_'] option:checked",
    "input[id^='product_attribute_'][type='radio']:checked + label",
    "input[id^='product_attribute_'][type='checkbox']:checked + label",
    ".attributes .selected-value",
]

PRODUCT_ATTRIBUTE_CONTAINER_SELECTORS = [
    ".attributes",
    ".product-essential .attributes",
    ".product-variant-line",
]

PRODUCT_REQUIRED_LABEL_SELECTORS = [
    ".attributes label.text-prompt",
    ".attributes dt",
    ".attributes .attribute-label",
    ".product-variant-line label",
]

PRODUCT_OPTION_CONTROL_SELECTORS = [
    "select[id^='product_attribute_']",
    "input[id^='product_attribute_'][type='radio']",
    "input[id^='product_attribute_'][type='checkbox']",
    "input[id^='product_attribute_'][type='text']",
    "textarea[id^='product_attribute_']",
]

PRODUCT_OPTION_PLACEHOLDER_SELECTORS = [
    "select[id^='product_attribute_'] option[selected]",
    "select[id^='product_attribute_'] option:checked",
]

PRODUCT_QUANTITY_SELECTORS = [
    "input[id*='EnteredQuantity']",
    "input[name*='EnteredQuantity']",
    "input.qty-input",
]

PRODUCT_SUMMARY_SELECTORS = [
    ".short-description",
    ".overview .short-description",
    ".full-description",
]

PRODUCT_RATING_SELECTORS = [
    ".product-review-box span",
    ".rating .review-score",
    ".product-review-links a",
]

PRODUCT_REVIEW_COUNT_SELECTORS = [
    ".product-review-links a",
    ".reviews-overview .product-review-links a",
    ".product-review-links span",
]

PRODUCT_BRAND_SELECTORS = [
    ".manufacturers a",
    ".manufacturer-part-number .value",
    ".sku .value",
]

PRODUCT_REVIEW_SNIPPET_SELECTORS = [
    ".product-review-list .review-text",
    ".product-review-item .review-text",
]

ACCESS_DENIED_TEXT_MARKERS = (
    "you don't have permission to access",
    "errors.edgesuite.net",
    "reference #",
)

CART_COUNT_SELECTORS = [
    "#topcartlink .cart-qty",
    ".cart-qty",
    ".shopping-cart-page .order-summary-content",
    ".shopping-cart-page .page-title",
]

CART_ROW_TITLE_SELECTORS = [
    "td.product a",
    ".product-name a",
    ".product a",
    "a[href]",
]

CART_ROW_LINK_SELECTORS = [
    "td.product a",
    ".product-name a",
    ".product a",
]

CART_ROW_PRICE_SELECTORS = [
    "td.subtotal span",
    "td.unit-price span",
    ".product-subtotal",
    ".product-unit-price",
    ".subtotal",
]

CART_ROW_QUANTITY_TEXT_SELECTORS = [
    "input.qty-input",
    "input[name*='itemquantity']",
    "input[name*='EnteredQuantity']",
    ".qty-input",
]

CART_ROW_VARIANT_SELECTORS = [
    ".attributes",
    ".sku .value",
    ".giftcard",
]

CART_TOTAL_SELECTORS = [
    ".cart-total .value-summary strong",
    ".cart-total-right .value-summary strong",
    ".totals .value-summary strong",
    ".order-subtotal .value-summary strong",
]

ORDER_TITLE_SELECTORS = [
    ".title a",
    ".product a",
    "a[href*='orderdetails']",
    "h2",
    "h3",
]

ORDER_ID_SELECTORS = [
    ".order-number",
    ".order-number strong",
    "bdi",
]

ORDER_DATE_SELECTORS = [
    ".order-date",
    ".created-on",
    ".date",
]

ORDER_STATUS_SELECTORS = [
    ".order-status",
    ".status",
    ".shipment-status",
]

ORDER_ETA_SELECTORS = [
    ".eta",
    ".delivery-date",
    ".shipment-status",
]

ORDER_TOTAL_SELECTORS = [
    ".order-total",
    ".total",
    ".price",
]

ORDER_RETURNS_LINK_SELECTORS = [
    "a[href*='return']",
    "a[href*='returns']",
    "a[href*='support']",
]

ORDER_SUPPORT_LINK_SELECTORS = [
    "a[href*='support']",
    "a[href*='help']",
    "a[href*='contact']",
]

SUCCESS_NOTIFICATION_SELECTORS = [
    ".bar-notification.success .content",
    ".bar-notification.success",
    "#bar-notification .content",
]

ERROR_NOTIFICATION_SELECTORS = [
    ".bar-notification.error .content",
    ".bar-notification.error",
    ".validation-summary-errors",
    ".field-validation-error",
    ".message-error",
]

GUEST_CHECKOUT_ENTRY_SELECTORS = [
    ".checkout-as-guest-button",
    "button:has-text('Checkout as Guest')",
    "input[value*='Checkout as Guest']",
]

TERMS_OF_SERVICE_SELECTORS = [
    "#termsofservice",
    "input[name='termsofservice']",
]

HOME_MARKER_SELECTORS = [
    ".home-page",
    ".homepage",
    ".home-page-category-grid",
    ".search-box-store-search-box",
]

GUEST_CHECKOUT_TEXT_MARKERS = (
    "checkout as guest",
    "register or checkout as guest",
    "welcome, please sign in",
)

CART_EMPTY_TEXT_MARKERS = (
    "your shopping cart is empty",
    "shopping cart is empty",
)

_JUNK_LINK_TOKENS = (
    "help",
    "support",
    "login",
    "register",
    "wishlist",
    "compareproducts",
    "customer",
    "cart",
)
_JUNK_TITLE_TOKENS = ("sponsored", "ad")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_lower(value: Any) -> str:
    return _normalize_text(value).lower()


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    digits = "".join(ch for ch in _normalize_text(value) if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _first(locator_or_page: Any) -> Any:
    return getattr(locator_or_page, "first", locator_or_page)


def _nth(locator_or_page: Any, index: int) -> Any:
    nth_method = getattr(locator_or_page, "nth", None)
    if callable(nth_method):
        try:
            return nth_method(index)
        except Exception:
            return _first(locator_or_page)
    return _first(locator_or_page)


def safe_locator(scope: Any, selector: str) -> Any | None:
    try:
        locator_fn = getattr(scope, "locator", None)
        if callable(locator_fn):
            return locator_fn(selector)
    except Exception:
        return None
    return None


def safe_count(locator_or_page: Any) -> int:
    count_fn = getattr(locator_or_page, "count", None)
    if not callable(count_fn):
        return 0
    try:
        value = count_fn()
    except Exception:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return 0


def safe_inner_text(target: Any, timeout_ms: int = 2500) -> str | None:
    inner_text_fn = getattr(target, "inner_text", None)
    if not callable(inner_text_fn):
        return None
    try:
        value = inner_text_fn(timeout=timeout_ms)
    except Exception:
        return None
    text = _normalize_text(value)
    return text or None


def safe_get_attribute(target: Any, attr_name: str, timeout_ms: int = 2500) -> str | None:
    get_attribute_fn = getattr(target, "get_attribute", None)
    if not callable(get_attribute_fn):
        return None
    try:
        value = get_attribute_fn(attr_name, timeout=timeout_ms)
    except Exception:
        return None
    text = _normalize_text(value)
    return text or None


def safe_is_checked(target: Any) -> bool | None:
    is_checked_fn = getattr(target, "is_checked", None)
    if callable(is_checked_fn):
        try:
            return bool(is_checked_fn())
        except Exception:
            return None
    checked_attr = safe_get_attribute(target, "checked")
    if checked_attr is not None:
        return True
    aria_checked = _normalize_lower(safe_get_attribute(target, "aria-checked"))
    if aria_checked in {"true", "false"}:
        return aria_checked == "true"
    return None


def safe_click(target: Any, timeout_ms: int = 4000) -> bool:
    click_fn = getattr(target, "click", None)
    if not callable(click_fn):
        return False
    try:
        click_fn(timeout=timeout_ms)
    except Exception:
        return False
    return True


def safe_fill(target: Any, value: str, timeout_ms: int = 4000) -> bool:
    fill_fn = getattr(target, "fill", None)
    if not callable(fill_fn):
        return False
    try:
        fill_fn(value, timeout=timeout_ms)
    except Exception:
        return False
    return True


def safe_select_option(target: Any, value: str) -> bool:
    select_option_fn = getattr(target, "select_option", None)
    if not callable(select_option_fn):
        return False
    try:
        select_option_fn(value)
    except Exception:
        return False
    return True


def safe_press(target: Any, key: str) -> bool:
    press_fn = getattr(target, "press", None)
    if not callable(press_fn):
        return False
    try:
        press_fn(key)
    except Exception:
        return False
    return True


def safe_is_visible(target: Any, timeout_ms: int = 2000) -> bool | None:
    is_visible_fn = getattr(target, "is_visible", None)
    if not callable(is_visible_fn):
        return None
    try:
        value = is_visible_fn(timeout=timeout_ms)
    except Exception:
        return None
    return bool(value)


def safe_wait_for_selector(page: Any, selector: str, timeout_ms: int = 4000) -> bool:
    wait_for_selector_fn = getattr(page, "wait_for_selector", None)
    if not callable(wait_for_selector_fn):
        return False
    try:
        wait_for_selector_fn(selector, timeout=timeout_ms)
    except Exception:
        return False
    return True


def safe_wait_for_load(page: Any, timeout_ms: int = 10000) -> bool:
    wait_for_load_state_fn = getattr(page, "wait_for_load_state", None)
    if not callable(wait_for_load_state_fn):
        return False
    try:
        wait_for_load_state_fn("domcontentloaded", timeout=timeout_ms)
    except Exception:
        return False
    return True


def safe_page_url(page: Any) -> str | None:
    try:
        value = getattr(page, "url", None)
    except Exception:
        return None
    text = _normalize_text(value)
    return text or None


def safe_page_title(page: Any) -> str | None:
    title_method = getattr(page, "title", None)
    if not callable(title_method):
        return None
    try:
        value = title_method()
    except Exception:
        return None
    text = _normalize_text(value)
    return text or None


def safe_body_text(page: Any, timeout_ms: int = 2500) -> str | None:
    body = safe_locator(page, "body")
    if body is None:
        return None
    return safe_inner_text(_first(body), timeout_ms=timeout_ms)


def safe_goto(page: Any, url: str, timeout_ms: int = 15000) -> bool:
    goto_fn = getattr(page, "goto", None)
    if not callable(goto_fn):
        return False
    try:
        goto_fn(url, wait_until="domcontentloaded", timeout=timeout_ms)
    except Exception:
        return False
    return True


def _parsed_url(url: str | None):
    try:
        return urlparse(_normalize_text(url))
    except Exception:
        return None


def _normalized_path(url: str | None) -> str:
    parsed = _parsed_url(url)
    if parsed is None:
        return ""
    return (parsed.path or "").strip().lower().rstrip("/")


def _is_demo_store_url(url: str | None) -> bool:
    parsed = _parsed_url(url)
    if parsed is None:
        return False
    return (parsed.hostname or "").lower().strip() == "demo.nopcommerce.com"


def _is_probable_product_url(url: str | None) -> bool:
    if not _is_demo_store_url(url):
        return False
    path = _normalized_path(url)
    if not path or path in {"", "/cart", "/search", "/login", "/register"}:
        return False
    reserved_prefixes = (
        "/search",
        "/cart",
        "/wishlist",
        "/compareproducts",
        "/customer",
        "/login",
        "/register",
        "/newproducts",
        "/recentlyviewedproducts",
    )
    return not path.startswith(reserved_prefixes)


def _contains_any(text: str | None, markers: tuple[str, ...]) -> bool:
    lowered = _normalize_lower(text)
    return any(marker in lowered for marker in markers)


def _extract_first_text(scope: Any, selectors: list[str]) -> str | None:
    for selector in selectors:
        locator = safe_locator(scope, selector)
        if locator is None:
            continue
        value = safe_inner_text(_first(locator))
        if value:
            return value
    return None


def _extract_first_attr(scope: Any, selectors: list[str], attr_name: str) -> str | None:
    for selector in selectors:
        locator = safe_locator(scope, selector)
        if locator is None:
            continue
        value = safe_get_attribute(_first(locator), attr_name)
        if value:
            return value
    return None


def _extract_text_list(scope: Any, selectors: list[str], limit: int = 6) -> list[str]:
    values: list[str] = []
    for selector in selectors:
        locator = safe_locator(scope, selector)
        if locator is None:
            continue
        count = safe_count(locator)
        for index in range(min(count, limit)):
            value = safe_inner_text(_nth(locator, index))
            if value and value not in values:
                values.append(value)
        if values:
            break
    return values


@dataclass
class SessionActionState:
    last_search_query: str | None = None
    last_search_url: str | None = None
    last_selected_product_url: str | None = None
    last_variant_signature: str | None = None
    last_add_to_cart_url: str | None = None
    last_checkout_url: str | None = None
    checkout_attempt_count: int = 0


class SessionActionGuard:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: dict[UUID, SessionActionState] = {}

    def clear(self) -> None:
        with self._lock:
            self._states.clear()

    def _get_state(self, session_id: UUID) -> SessionActionState:
        state = self._states.get(session_id)
        if state is None:
            state = SessionActionState()
            self._states[session_id] = state
        return state

    def should_skip_duplicate_search(
        self,
        session_id: UUID,
        *,
        query: str | None,
        current_url: str | None,
    ) -> bool:
        query_text = _normalize_lower(query)
        if not query_text:
            return False
        with self._lock:
            state = self._get_state(session_id)
            if _normalize_lower(state.last_search_query) != query_text:
                return False
            return _query_matches_url(query_text, current_url)

    def record_search(self, session_id: UUID, *, query: str | None, current_url: str | None) -> None:
        with self._lock:
            state = self._get_state(session_id)
            state.last_search_query = _normalize_text(query) or None
            state.last_search_url = current_url

    def should_skip_duplicate_product_open(self, session_id: UUID, *, current_url: str | None) -> bool:
        url_text = _normalize_lower(current_url)
        if not _is_probable_product_url(current_url):
            return False
        with self._lock:
            state = self._get_state(session_id)
            if not state.last_selected_product_url:
                return False
            return _normalize_lower(state.last_selected_product_url) == url_text

    def record_product_open(self, session_id: UUID, *, current_url: str | None) -> None:
        if not current_url:
            return
        with self._lock:
            state = self._get_state(session_id)
            state.last_selected_product_url = current_url

    def should_skip_duplicate_variant_selection(
        self,
        session_id: UUID,
        *,
        signature: str | None,
        current_url: str | None,
    ) -> bool:
        signature_text = _normalize_lower(signature)
        if not signature_text:
            return False
        with self._lock:
            state = self._get_state(session_id)
            if _normalize_lower(state.last_variant_signature) != signature_text:
                return False
            return _normalize_lower(state.last_selected_product_url) == _normalize_lower(current_url)

    def record_variant_selection(
        self,
        session_id: UUID,
        *,
        signature: str | None,
        current_url: str | None,
    ) -> None:
        signature_text = _normalize_text(signature) or None
        if signature_text is None:
            return
        with self._lock:
            state = self._get_state(session_id)
            state.last_variant_signature = signature_text
            state.last_selected_product_url = current_url

    def should_skip_duplicate_add_to_cart(self, session_id: UUID, *, current_url: str | None) -> bool:
        url_text = _normalize_lower(current_url)
        if not url_text:
            return False
        if "cart" in url_text:
            return True
        with self._lock:
            state = self._get_state(session_id)
            return _normalize_lower(state.last_add_to_cart_url) == url_text

    def record_add_to_cart(self, session_id: UUID, *, current_url: str | None) -> None:
        with self._lock:
            state = self._get_state(session_id)
            state.last_add_to_cart_url = current_url

    def should_skip_duplicate_checkout_attempt(
        self,
        session_id: UUID,
        *,
        current_url: str | None,
    ) -> bool:
        url_text = _normalize_lower(current_url)
        if not url_text:
            return False
        if "checkout" in url_text:
            return True

        with self._lock:
            state = self._get_state(session_id)
            if _normalize_lower(state.last_checkout_url) != url_text:
                return False
            return state.checkout_attempt_count >= 1

    def record_checkout_attempt(self, session_id: UUID, *, current_url: str | None) -> None:
        with self._lock:
            state = self._get_state(session_id)
            if _normalize_lower(state.last_checkout_url) == _normalize_lower(current_url):
                state.checkout_attempt_count += 1
            else:
                state.last_checkout_url = current_url
                state.checkout_attempt_count = 1


action_guard = SessionActionGuard()


def _query_matches_url(query: str, url: str | None) -> bool:
    parsed = _parsed_url(url)
    if parsed is None:
        return False
    path = (parsed.path or "").lower()
    if "/search" not in path:
        return False
    qs = parse_qs(parsed.query or "")
    query_values = [value for value in qs.get("q", []) if value]
    if not query_values:
        return False
    url_text = _normalize_lower(" ".join(query_values))
    condensed = "+".join(part for part in query.split() if part)
    encoded = quote_plus(query)
    normalized_query = _normalize_lower(query)
    return (
        condensed in _normalize_lower(url)
        or encoded in _normalize_lower(url)
        or normalized_query in url_text
    )


def dismiss_common_interruptions(page: Any) -> list[str]:
    notes: list[str] = []
    dismissed = 0
    for selector in MODAL_DISMISS_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        target = _first(locator)
        visible = safe_is_visible(target, timeout_ms=250)
        if visible is False:
            continue
        if safe_click(target, timeout_ms=600):
            notes.append(f"dismissed:{selector}")
            dismissed += 1
        if dismissed >= 2:
            break
    return notes


def detect_location_blocked(page: Any) -> bool:
    """Returns True if a merchant modal is blocking the current page."""
    for selector in BB_LOCATION_MODAL_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        if safe_is_visible(_first(locator)) is not False:
            return True
    return False


def detect_access_denied(page: Any) -> bool:
    title = _normalize_lower(safe_page_title(page))
    body = _normalize_lower(safe_body_text(page))
    combined = " ".join(part for part in [title, body] if part)
    if title == "access denied":
        return True
    return any(marker in combined for marker in ACCESS_DENIED_TEXT_MARKERS)


def _guest_checkout_entry_visible(page: Any, *, url: str | None = None, body: str | None = None) -> bool:
    if "/login/checkoutasguest" in _normalize_lower(url):
        return True
    if _contains_any(body, GUEST_CHECKOUT_TEXT_MARKERS):
        return True
    return _has_visible_selector(page, GUEST_CHECKOUT_ENTRY_SELECTORS)


def _listing_grid_visible(page: Any) -> bool:
    return _has_visible_selector(page, SEARCH_RESULT_CONTAINER_SELECTORS)


def _home_visible(page: Any, *, path: str, body: str, title: str) -> bool:
    if path in {"", "/"} and _contains_any(f"{title} {body}", ("welcome to our store", "demo store")):
        return True
    return path in {"", "/"} and _has_visible_selector(page, HOME_MARKER_SELECTORS)


def _search_surface_visible(page: Any, *, path: str, body: str) -> bool:
    if path == "/search":
        return True
    if _listing_grid_visible(page):
        return True
    return _has_visible_selector(page, SEARCH_PAGE_ANCHOR_SELECTORS) and "search keyword" in body


def _product_surface_visible(page: Any) -> bool:
    if not _has_visible_selector(page, PRODUCT_ANCHOR_SELECTORS):
        return False
    return not _listing_grid_visible(page)


def _cart_surface_visible(page: Any, *, path: str, title: str, body: str) -> bool:
    if path == "/cart":
        return True
    if "shopping cart" in title or _contains_any(body, CART_EMPTY_TEXT_MARKERS):
        return True
    return _has_visible_selector(page, CART_ANCHOR_SELECTORS)


def classify_page_state(page: Any) -> str:
    """
    Classify the current browser page into a named state.
    Returns one of:
      'blank' | 'login' | 'checkout' | 'cart' | 'product' | 'search_results' | 'home' | 'unknown'
    This is used as a pre-action guard in route handlers.
    """
    url = safe_page_url(page)
    url_text = _normalize_lower(url)
    if not url_text or url_text == "about:blank":
        return "blank"
    if detect_access_denied(page):
        return "unknown"
    path = _normalized_path(url)
    title = _normalize_lower(safe_page_title(page))
    body = _normalize_lower(safe_body_text(page))

    if _guest_checkout_entry_visible(page, url=url, body=body):
        return "checkout"
    if "checkout" in url_text or _has_visible_selector(page, CHECKOUT_ANCHOR_SELECTORS):
        return "checkout"
    if _cart_surface_visible(page, path=path, title=title, body=body):
        return "cart"
    if "login" in url_text or "signin" in url_text or "sign-in" in url_text:
        return "login"
    if _home_visible(page, path=path, body=body, title=title):
        return "home"
    if _product_surface_visible(page):
        return "product"
    if _search_surface_visible(page, path=path, body=body):
        return "search_results"
    if _is_demo_store_url(url):
        return "home"
    return "unknown"


def collect_semantic_page_signals(page: Any) -> list[str]:
    signals: list[str] = []
    groups = [
        ("captcha_visible", CAPTCHA_SELECTORS),
        ("otp_required", OTP_SELECTORS),
        ("payment_auth_required", PAYMENT_AUTH_SELECTORS),
        ("product_anchor_present", PRODUCT_ANCHOR_SELECTORS),
        ("cart_anchor_present", CART_ANCHOR_SELECTORS),
        ("checkout_anchor_present", CHECKOUT_ANCHOR_SELECTORS),
    ]
    for label, selectors in groups:
        for selector in selectors:
            locator = safe_locator(page, selector)
            if locator is None or safe_count(locator) <= 0:
                continue
            visible = safe_is_visible(_first(locator))
            if visible is False:
                continue
            signals.append(label)
            break
    return signals


def _has_visible_selector(scope: Any, selectors: list[str]) -> bool:
    for selector in selectors:
        locator = safe_locator(scope, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        visible = safe_is_visible(_first(locator))
        if visible is False:
            continue
        return True
    return False


def _run_stabilization_pass(
    page: Any,
    *,
    anchor_selectors: list[str],
    wait_selectors: list[str],
    note_prefix: str,
) -> list[str]:
    if not _has_visible_selector(page, anchor_selectors):
        return []
    notes = [f"{note_prefix}:anchor_detected"]
    safe_wait_for_load(page, timeout_ms=5000)
    for selector in wait_selectors:
        if safe_wait_for_selector(page, selector, timeout_ms=2500):
            notes.append(f"{note_prefix}:waited:{selector}")
            break
    return notes


def submit_search_query(page: Any, query: str | None) -> tuple[bool, list[str]]:
    notes: list[str] = []
    query_text = _normalize_text(query)
    if not query_text:
        notes.append("query_missing")
        return False, notes

    if detect_location_blocked(page):
        notes.append("location_blocked")
        return False, notes

    page_state = classify_page_state(page)
    if page_state == "login":
        notes.append("sign_in_required")
        return False, notes
    if page_state == "checkout":
        notes.append("unexpected_checkout_state")
        return False, notes

    current_url = safe_page_url(page)
    if _query_matches_url(query_text, current_url):
        notes.append("search_results_already_loaded")
        return True, notes

    for attempt in range(2):
        target = None
        for selector in SEARCH_INPUT_SELECTORS:
            safe_wait_for_selector(page, selector, timeout_ms=1000)
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            candidate = _first(locator)
            visible = safe_is_visible(candidate, timeout_ms=300)
            if visible is False:
                continue
            target = candidate
            break

        if target is None:
            notes.append("search_box_not_found")
            return False, notes

        if not safe_fill(target, query_text, timeout_ms=1000):
            notes.append("search_fill_failed")
            return False, notes

        for selector in SEARCH_SUBMIT_SELECTORS:
            submitter = safe_locator(page, selector)
            if submitter is None or safe_count(submitter) <= 0:
                continue
            target_button = _first(submitter)
            visible = safe_is_visible(target_button)
            if visible is False:
                continue
            if safe_click(target_button, timeout_ms=1500):
                safe_wait_for_load(page, timeout_ms=4000)
                return True, notes

        if safe_press(target, "Enter"):
            safe_wait_for_load(page, timeout_ms=4000)
            return True, notes

        notes.append("search_submit_failed")
        return False, notes

    notes.append("search_submit_unresolved")
    return False, notes


def collect_search_result_candidates(page: Any, limit: int = 8) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for container_selector in SEARCH_RESULT_CONTAINER_SELECTORS:
        containers = safe_locator(page, container_selector)
        container_count = safe_count(containers) if containers is not None else 0

        for index in range(min(limit, container_count)):
            container = _nth(containers, index)
            title = _extract_first_text(container, SEARCH_RESULT_TITLE_SELECTORS)
            url = _extract_first_attr(container, SEARCH_RESULT_LINK_SELECTORS, "href")
            if url and url.startswith("/"):
                url = urljoin(BB_HOME_URL, url)
            if url and not _is_probable_product_url(url):
                continue

            price = _extract_first_text(container, SEARCH_RESULT_PRICE_SELECTORS)
            summary_text = _extract_first_text(container, SEARCH_RESULT_SUMMARY_SELECTORS)
            rating = _extract_first_text(container, PRODUCT_RATING_SELECTORS)
            review_count = _extract_first_text(container, PRODUCT_REVIEW_COUNT_SELECTORS)
            availability = _extract_first_text(
                container,
                [
                    ".stock",
                    ".availability",
                    ".buttons button",
                    ".buttons input",
                    ".add-to-cart-button",
                    "button[id^='add-to-cart-button-']",
                ],
            )

            candidate = {
                "title": title,
                "price_text": price,
                "url": url,
                "summary_text": summary_text,
                "quantity_text": None,
                "rating_text": rating,
                "review_count_text": review_count,
                "availability_text": availability,
                "variant_text": None,
            }
            candidate_key = "|".join(
                [
                    _normalize_lower(candidate.get("url")),
                    _normalize_lower(candidate.get("title")),
                ]
            )
            if not any(value for value in candidate.values()):
                continue
            if candidate_key in seen_keys:
                continue
            seen_keys.add(candidate_key)
            candidates.append(candidate)
        if candidates:
            break

    if candidates:
        return candidates

    for selector in SEARCH_RESULT_LINK_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        count = safe_count(locator)
        for index in range(min(limit, count)):
            link = _nth(locator, index)
            href = safe_get_attribute(link, "href")
            title = safe_inner_text(link)
            if href and href.startswith("/"):
                href = urljoin(BB_HOME_URL, href)
            if href and not _is_probable_product_url(href):
                continue
            candidate = {
                "title": title,
                "price_text": None,
                "url": href,
                "summary_text": None,
                "quantity_text": None,
                "rating_text": None,
                "review_count_text": None,
                "availability_text": None,
                "variant_text": None,
            }
            candidate_key = "|".join([_normalize_lower(href), _normalize_lower(title)])
            if candidate_key in seen_keys:
                continue
            if title or href:
                seen_keys.add(candidate_key)
                candidates.append(candidate)
        if candidates:
            break

    return candidates


def choose_best_product_candidate(
    candidates: list[dict[str, Any]],
    *,
    query: str | None = None,
    return_scores: bool = False,
) -> dict[str, Any] | None | tuple[dict[str, Any] | None, list[tuple[int, dict[str, Any]]]]:
    import re as _re

    best: dict[str, Any] | None = None
    best_score = -10_000
    query_tokens: list[str] = []
    size_tokens: list[str] = []
    _scored_list: list[tuple[int, dict[str, Any]]] = []
    if query:
        q_lower = query.lower()
        size_tokens = _re.findall(r"\d+\s*(?:kg|g|ml|l|gm|ltr|litre|pack|pcs|pc)\b", q_lower)
        _STOP = {"a", "an", "the", "of", "for", "and", "or", "with", "in", "on"}
        query_tokens = [w for w in q_lower.split() if len(w) > 2 and w not in _STOP]

    for candidate in candidates:
        url = _normalize_lower(candidate.get("url"))
        title = _normalize_lower(candidate.get("title"))
        summary = _normalize_lower(candidate.get("summary_text"))
        availability = _normalize_lower(candidate.get("availability_text"))
        price = _normalize_text(candidate.get("price_text"))

        score = 0
        if title:
            score += 4
        if url:
            score += 2
        if price:
            score += 2
        if summary:
            score += 1
        if _is_probable_product_url(url):
            score += 8
        elif _is_demo_store_url(url):
            score -= 4
        if any(token in url for token in _JUNK_LINK_TOKENS):
            score -= 6
        if any(token in title for token in _JUNK_TITLE_TOKENS):
            score -= 4
        if not url:
            score -= 2
        if any(token in availability for token in ("out of stock", "unavailable")):
            score -= 3
        if query_tokens:
            for token in query_tokens:
                if token in title:
                    score += 3
                elif token in summary:
                    score += 1
                elif token in url:
                    score += 1
        if size_tokens:
            _title_nospace = _re.sub(r"\s+", "", title)
            matched_size = any(
                _re.sub(r"\s+", "", s) in _title_nospace
                for s in size_tokens
            )
            if matched_size:
                score += 5
            else:
                score -= 2

        _scored_list.append((score, candidate))

        if score > best_score:
            best_score = score
            best = candidate

    scored: list[tuple[int, dict[str, Any]]] = sorted(
        _scored_list,
        key=lambda x: x[0],
        reverse=True,
    )

    if best is None or best_score <= 0:
        if return_scores:
            return None, scored
        return None
    if return_scores:
        return best, scored
    return best


def _is_score_tie(
    scored: list[tuple[int, dict[str, Any]]],
    threshold: int = 2,
) -> bool:
    """
    Returns True if the top 2 candidates are within `threshold` points.
    Used by the caller to decide whether to invoke Gemini for tie-breaking.
    """
    if len(scored) < 2:
        return False
    return abs(scored[0][0] - scored[1][0]) <= threshold


def open_best_search_result(
    page: Any,
    *,
    session_id: UUID,
    query: str | None = None,
) -> tuple[bool, dict[str, Any] | None, list[str]]:
    notes: list[str] = []
    current_url = safe_page_url(page)
    if action_guard.should_skip_duplicate_product_open(session_id, current_url=current_url):
        notes.append("duplicate_product_open_skipped")
        return False, None, notes

    candidates = collect_search_result_candidates(page)
    candidate = choose_best_product_candidate(candidates, query=query)
    if candidate is None:
        notes.append("candidate_not_found")
        return False, None, notes

    candidate_url = _normalize_text(candidate.get("url")) or None
    opened = False
    if candidate_url:
        opened = safe_goto(page, candidate_url)
        if not opened:
            notes.append("candidate_navigation_failed")
    else:
        link = safe_locator(page, SEARCH_RESULT_LINK_SELECTORS[0])
        if link is not None:
            opened = safe_click(_first(link))
            if opened:
                safe_wait_for_load(page)
            else:
                notes.append("candidate_click_failed")

    if opened:
        action_guard.record_product_open(session_id, current_url=safe_page_url(page))
    return opened, candidate, notes


def extract_product_detail_evidence(page: Any) -> dict[str, Any]:
    import re as _re

    def _read_notification_texts(selectors: list[str], limit: int = 4) -> list[str]:
        texts: list[str] = []
        for selector in selectors:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            count = safe_count(locator)
            for index in range(min(count, limit)):
                target = _nth(locator, index)
                visible = safe_is_visible(target)
                if visible is False:
                    continue
                text = safe_inner_text(target)
                if text and text not in texts:
                    texts.append(text)
            if texts:
                break
        return texts

    def _selected_option_details(select_control: Any) -> tuple[str | None, str | None]:
        for selector in ["option:checked", "option[selected]"]:
            option_locator = safe_locator(select_control, selector)
            if option_locator is None or safe_count(option_locator) <= 0:
                continue
            option = _first(option_locator)
            return safe_inner_text(option), safe_get_attribute(option, "value")
        return None, safe_get_attribute(select_control, "value")

    def _collect_selected_variant_values() -> list[str]:
        selected_values: list[str] = []
        selected_values.extend(_extract_text_list(page, PRODUCT_VARIANT_VALUE_SELECTORS, limit=8))
        select_locator = safe_locator(page, "select[id^='product_attribute_']")
        if select_locator is not None:
            for index in range(min(safe_count(select_locator), 8)):
                selected_text, _ = _selected_option_details(_nth(select_locator, index))
                if selected_text and selected_text not in selected_values:
                    lowered = _normalize_lower(selected_text)
                    if not any(token in lowered for token in ("please select", "choose", "--")):
                        selected_values.append(selected_text)
        return selected_values

    def _extract_quantity_details() -> tuple[str | None, int | None]:
        min_qty: int | None = None
        quantity_text: str | None = None
        for selector in PRODUCT_QUANTITY_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None or safe_count(locator) <= 0:
                continue
            target = _first(locator)
            value = safe_get_attribute(target, "value")
            min_value = _parse_int(safe_get_attribute(target, "min"))
            parts: list[str] = []
            if value:
                parts.append(f"Qty: {value}")
            if min_value is not None and min_value > 1:
                parts.append(f"Minimum quantity: {min_value}")
            quantity_text = ", ".join(parts) or None
            min_qty = min_value
            break

        body = _normalize_lower(safe_body_text(page))
        if min_qty is None:
            match = _re.search(r"minimum quantity[^0-9]*(\d+)", body)
            if match:
                min_qty = _parse_int(match.group(1))
        if quantity_text is None and min_qty is not None and min_qty > 1:
            quantity_text = f"Minimum quantity: {min_qty}"
        return quantity_text, min_qty

    option_labels = _extract_text_list(page, PRODUCT_REQUIRED_LABEL_SELECTORS, limit=10)
    variant_options = [label for label in option_labels if label]
    selected_variants = _collect_selected_variant_values()
    review_snippets = _extract_text_list(page, PRODUCT_REVIEW_SNIPPET_SELECTORS, limit=4)
    summary_text = _extract_first_text(page, PRODUCT_SUMMARY_SELECTORS)
    quantity_text, min_qty = _extract_quantity_details()
    availability_text = _extract_first_text(page, PRODUCT_AVAILABILITY_SELECTORS)
    if availability_text is None and _has_visible_selector(page, ADD_TO_CART_BUTTON_SELECTORS):
        availability_text = "Add to cart available"

    error_texts = _read_notification_texts(ERROR_NOTIFICATION_SELECTORS)
    notes: list[str] = []
    blocker_hints: list[str] = []

    has_required_labels = any(
        "*" in label or "required" in _normalize_lower(label)
        for label in option_labels
    )
    pending_required_select = False
    select_locator = safe_locator(page, "select[id^='product_attribute_']")
    if select_locator is not None:
        for index in range(min(safe_count(select_locator), 8)):
            selected_text, selected_value = _selected_option_details(_nth(select_locator, index))
            selected_label = _normalize_lower(selected_text or selected_value)
            if (
                not selected_label
                or selected_value in {"", "0"}
                or any(token in selected_label for token in ("please select", "choose", "--"))
            ):
                pending_required_select = True
                break

    radio_checkbox_controls = safe_locator(
        page,
        "input[id^='product_attribute_'][type='radio'], input[id^='product_attribute_'][type='checkbox']",
    )
    radio_checkbox_present = radio_checkbox_controls is not None and safe_count(radio_checkbox_controls) > 0
    radio_checkbox_selected = False
    if radio_checkbox_present:
        for index in range(min(safe_count(radio_checkbox_controls), 16)):
            checked = safe_is_checked(_nth(radio_checkbox_controls, index))
            if checked:
                radio_checkbox_selected = True
                break

    text_controls = safe_locator(
        page,
        "input[id^='product_attribute_'][type='text'], textarea[id^='product_attribute_']",
    )
    text_required_missing = False
    if text_controls is not None and safe_count(text_controls) > 0 and has_required_labels:
        for index in range(min(safe_count(text_controls), 8)):
            value = _normalize_text(safe_get_attribute(_nth(text_controls, index), "value"))
            if not value:
                text_required_missing = True
                break

    combined_error_text = " ".join(_normalize_lower(text) for text in error_texts)
    if "please select" in combined_error_text or "required" in combined_error_text:
        pending_required_select = True
    if "minimum quantity" in combined_error_text and "minimum_quantity_required" not in blocker_hints:
        blocker_hints.append("minimum_quantity_required")

    controls_present = _has_visible_selector(page, PRODUCT_OPTION_CONTROL_SELECTORS)
    if controls_present and (
        pending_required_select
        or (has_required_labels and radio_checkbox_present and not radio_checkbox_selected)
        or text_required_missing
    ):
        blocker_hints.append("option_selection_required")
        notes.append("option_selection_required")
        if option_labels:
            notes.append(f"required_options:{'; '.join(option_labels[:4])}")

    if min_qty is not None and min_qty > 1 and "minimum_quantity_required" not in blocker_hints:
        blocker_hints.append("minimum_quantity_required")
    if min_qty is not None and min_qty > 1:
        notes.append(f"minimum_quantity_required:{min_qty}")

    evidence = {
        "title": _extract_first_text(page, PRODUCT_TITLE_SELECTORS),
        "price_text": _extract_first_text(page, PRODUCT_PRICE_SELECTORS),
        "availability_text": availability_text,
        "summary_text": summary_text,
        "quantity_text": quantity_text,
        "variant_text": " / ".join(selected_variants) if selected_variants else None,
        "rating_text": _extract_first_text(page, PRODUCT_RATING_SELECTORS),
        "review_count_text": _extract_first_text(page, PRODUCT_REVIEW_COUNT_SELECTORS),
        "brand_text": _extract_first_text(page, PRODUCT_BRAND_SELECTORS),
        "review_snippets": review_snippets,
        "variant_options": variant_options,
        "blocker_hints": blocker_hints,
        "url": safe_page_url(page),
        "page_title": safe_page_title(page),
    }
    if not evidence["title"]:
        notes.append("title_missing")
    if not evidence["price_text"]:
        notes.append("price_missing")
    if error_texts:
        notes.extend(f"page_error:{text}" for text in error_texts[:2])
    evidence["notes"] = ", ".join(dict.fromkeys(note for note in notes if note)) or None
    return evidence


def select_variant_option(
    page: Any,
    *,
    session_id: UUID,
    variant_hint: str | None = None,
    size_hint: str | None = None,
    color_hint: str | None = None,
) -> tuple[bool, list[str], str | None]:
    hints: list[str] = []
    for value in [variant_hint, size_hint, color_hint]:
        text = _normalize_text(value)
        if text:
            hints.append(text)

    signature = "|".join(part.lower() for part in hints) if hints else None
    notes: list[str] = []
    current_url = safe_page_url(page)

    if action_guard.should_skip_duplicate_variant_selection(
        session_id,
        signature=signature,
        current_url=current_url,
    ):
        notes.append("duplicate_variant_selection_skipped")
        return True, notes, signature

    if not hints:
        notes.append("variant_hint_missing")
        return False, notes, signature

    def _hint_matches(option_text: str | None) -> bool:
        lowered = _normalize_lower(option_text)
        return bool(lowered) and any(hint.lower() in lowered for hint in hints)

    for attempt in range(2):
        select_locator = safe_locator(page, "select[id^='product_attribute_']")
        if select_locator is not None:
            for index in range(min(safe_count(select_locator), 8)):
                control = _nth(select_locator, index)
                for option_selector in ["option", "option:checked", "option[selected]"]:
                    options = safe_locator(control, option_selector)
                    if options is None or safe_count(options) <= 0:
                        continue
                    for option_index in range(min(safe_count(options), 16)):
                        option = _nth(options, option_index)
                        option_text = safe_inner_text(option)
                        if not _hint_matches(option_text):
                            continue
                        option_value = safe_get_attribute(option, "value") or option_text
                        if not option_value:
                            continue
                        if not safe_select_option(control, option_value):
                            continue
                        safe_wait_for_load(page, timeout_ms=5000)
                        notes.append(f"variant_selected:select:{index}")
                        action_guard.record_variant_selection(
                            session_id,
                            signature=signature,
                            current_url=safe_page_url(page),
                        )
                        return True, notes, signature

        for selector in VARIANT_OPTION_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            count = safe_count(locator)
            if count <= 0:
                continue

            for index in range(min(count, 12)):
                option = _nth(locator, index)
                option_text = safe_inner_text(option) or safe_get_attribute(option, "value")
                if not _hint_matches(option_text):
                    continue
                if not safe_click(option):
                    continue
                safe_wait_for_load(page, timeout_ms=5000)
                notes.append(f"variant_selected:{selector}:{index}")
                action_guard.record_variant_selection(
                    session_id,
                    signature=signature,
                    current_url=safe_page_url(page),
                )
                return True, notes, signature

        if attempt == 0:
            notes.extend(
                _run_stabilization_pass(
                    page,
                    anchor_selectors=PRODUCT_ANCHOR_SELECTORS,
                    wait_selectors=VARIANT_OPTION_SELECTORS,
                    note_prefix="variant_ui_stabilization_retry",
                )
            )

    notes.append("variant_option_not_found")
    return False, notes, signature


def _read_cart_badge_count(page: Any) -> int | None:
    """Read the current cart item count from the header badge. Returns None if unreadable."""
    for selector in CART_COUNT_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        text = safe_inner_text(_first(locator))
        parsed = _parse_int(text)
        if parsed is not None:
            return parsed
    return None


def _verify_add_to_cart_evidence(page: Any, pre_count: int | None) -> tuple[bool, list[str]]:
    """
    Returns verified status plus evidence notes after an add-to-cart click.
    """
    import time

    notes: list[str] = []
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        for selector in SUCCESS_NOTIFICATION_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None or safe_count(locator) <= 0:
                continue
            text = _normalize_lower(safe_inner_text(_first(locator)))
            if "added to your shopping cart" in text or "the product has been added" in text:
                notes.append("success_notification_visible")
                return True, notes
        for selector in ERROR_NOTIFICATION_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None or safe_count(locator) <= 0:
                continue
            text = safe_inner_text(_first(locator))
            lowered = _normalize_lower(text)
            if not lowered:
                continue
            if "please select" in lowered or "required" in lowered:
                notes.append("option_selection_required")
            if "minimum quantity" in lowered:
                notes.append("minimum_quantity_required")
            notes.append(f"add_to_cart_error:{text}")
            return False, notes
        post_count = _read_cart_badge_count(page)
        if post_count is not None:
            pre = pre_count if pre_count is not None else 0
            if post_count > pre:
                notes.append("cart_badge_incremented")
                return True, notes
        for selector in BB_QUANTITY_STEPPER_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is not None and safe_count(locator) > 0:
                if safe_is_visible(_first(locator)) is not False:
                    notes.append(f"post_add_signal:{selector}")
                    return True, notes
        if classify_page_state(page) == "cart":
            cart_evidence = extract_cart_evidence(page)
            if (cart_evidence.get("cart_item_count") or 0) > 0:
                notes.append("cart_page_confirmed")
                return True, notes
        time.sleep(0.3)
    return False, notes


def add_current_product_to_cart(page: Any, *, session_id: UUID) -> tuple[bool, list[str]]:
    notes: list[str] = []
    current_url = safe_page_url(page)
    if action_guard.should_skip_duplicate_add_to_cart(session_id, current_url=current_url):
        notes.append("duplicate_add_to_cart_skipped")
        return True, notes

    page_state = classify_page_state(page)
    if page_state != "product":
        notes.append(f"unexpected_page_state:{page_state}")
        return False, notes

    detail_evidence = extract_product_detail_evidence(page)
    detail_notes = _normalize_text(detail_evidence.get("notes"))
    blocker_hints = detail_evidence.get("blocker_hints") or []
    if "option_selection_required" in blocker_hints:
        notes.append("option_selection_required")
        if detail_notes:
            notes.append(detail_notes)
        return False, notes
    if "minimum_quantity_required" in blocker_hints:
        notes.append("minimum_quantity_required")
        if detail_notes:
            notes.append(detail_notes)
        return False, notes

    pre_count = _read_cart_badge_count(page)
    _REJECT_BUTTON_TEXTS = (
        "notify", "notify me", "wishlist", "login", "subscribe",
        "view", "explore", "replace", "quick view", "see all",
        "know more", "out of stock", "unavailable",
    )

    for attempt in range(2):
        for selector in ADD_TO_CART_BUTTON_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            if safe_count(locator) <= 0:
                continue
            for idx in range(min(safe_count(locator), 4)):
                target = _nth(locator, idx)
                visible = safe_is_visible(target)
                if visible is False:
                    continue
                btn_text = _normalize_lower(safe_inner_text(target, timeout_ms=1000) or "")
                if any(bad in btn_text for bad in _REJECT_BUTTON_TEXTS):
                    notes.append(f"rejected_button:{btn_text[:30]}")
                    continue
                if not safe_click(target):
                    continue
                safe_wait_for_load(page)
                verified, verification_notes = _verify_add_to_cart_evidence(page, pre_count)
                notes.extend(verification_notes)
                if verified:
                    action_guard.record_add_to_cart(session_id, current_url=safe_page_url(page))
                    notes.append(f"add_to_cart_verified:{selector}")
                    return True, notes
                notes.append(f"add_to_cart_clicked_unverified:{selector}")
        if attempt == 0:
            notes.extend(
                _run_stabilization_pass(
                    page,
                    anchor_selectors=PRODUCT_ANCHOR_SELECTORS,
                    wait_selectors=ADD_TO_CART_BUTTON_SELECTORS,
                    note_prefix="add_to_cart_ui_stabilization_retry",
                )
            )

    notes.append("add_to_cart_button_not_found_or_unverified")
    return False, notes


def detect_checkout_entry_readiness(page: Any) -> tuple[bool | None, list[str]]:
    notes: list[str] = []
    url = safe_page_url(page)
    url_text = _normalize_lower(url)
    body = safe_body_text(page)
    if _guest_checkout_entry_visible(page, url=url, body=body):
        notes.append("guest_checkout_entry_visible")
        return True, notes
    if "checkout" in url_text:
        notes.append("already_in_checkout_path")
        return True, notes
    if _contains_any(body, CART_EMPTY_TEXT_MARKERS):
        notes.append("cart_empty")
        return False, notes

    for selector in TERMS_OF_SERVICE_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        checked = safe_is_checked(_first(locator))
        if checked is False:
            notes.append("terms_of_service_required")
        elif checked is True:
            notes.append("terms_of_service_checked")
        break

    seen_any = False
    for selector in CHECKOUT_BUTTON_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        count = safe_count(locator)
        if count <= 0:
            continue
        seen_any = True
        target = _first(locator)
        visible = safe_is_visible(target)
        if visible is False:
            continue
        notes.append(f"checkout_button_detected:{selector}")
        return True, notes

    if seen_any:
        notes.append("checkout_button_hidden")
        return False, notes
    notes.append("checkout_signal_weak")
    return None, notes


def attempt_checkout_entry(page: Any) -> tuple[bool, list[str]]:
    notes: list[str] = []
    for attempt in range(2):
        if _guest_checkout_entry_visible(page, url=safe_page_url(page), body=safe_body_text(page)):
            notes.append("guest_checkout_entry_visible")
            return True, notes
        ready, readiness_notes = detect_checkout_entry_readiness(page)
        notes.extend(readiness_notes)
        if ready is True:
            current_url = _normalize_lower(safe_page_url(page))
            if "checkout" in current_url:
                return True, notes
            for selector in TERMS_OF_SERVICE_SELECTORS:
                locator = safe_locator(page, selector)
                if locator is None or safe_count(locator) <= 0:
                    continue
                target = _first(locator)
                checked = safe_is_checked(target)
                if checked is False and safe_click(target):
                    notes.append("terms_of_service_checked")
                    safe_wait_for_load(page, timeout_ms=2000)
                break
            for selector in CHECKOUT_BUTTON_SELECTORS:
                locator = safe_locator(page, selector)
                if locator is None:
                    continue
                target = _first(locator)
                visible = safe_is_visible(target)
                if visible is False:
                    continue
                if safe_click(target):
                    safe_wait_for_load(page)
                    notes.append("checkout_click_attempted")
                    if _guest_checkout_entry_visible(page, url=safe_page_url(page), body=safe_body_text(page)):
                        notes.append("checkout_entry_reached")
                        return True, notes
                    if classify_page_state(page) == "checkout":
                        notes.append("checkout_state_confirmed")
                        return True, notes
                    notes.append("checkout_click_unverified")
                    return False, notes
            notes.append("checkout_click_not_executed")
            return False, notes
        if attempt == 0:
            notes.extend(
                _run_stabilization_pass(
                    page,
                    anchor_selectors=CART_ANCHOR_SELECTORS,
                    wait_selectors=CHECKOUT_BUTTON_SELECTORS,
                    note_prefix="checkout_ui_stabilization_retry",
                )
            )
    return False, notes


def extract_cart_evidence(page: Any) -> dict[str, Any]:
    cart_items: list[dict[str, Any]] = []
    count_from_subtotal = _read_cart_badge_count(page)
    row_count = 0
    for selector in CART_ROW_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        count = safe_count(locator)
        row_count = max(row_count, count)
        for index in range(min(count, 12)):
            row = _nth(locator, index)
            title = _extract_first_text(row, CART_ROW_TITLE_SELECTORS)
            url = _extract_first_attr(row, CART_ROW_LINK_SELECTORS, "href")
            if url and url.startswith("/"):
                url = urljoin(BB_HOME_URL, url)
            price_text = _extract_first_text(row, CART_ROW_PRICE_SELECTORS)
            quantity_locator = safe_locator(row, "input[name*='quantity'], input[name*='qty']")
            quantity_text = _extract_first_text(row, CART_ROW_QUANTITY_TEXT_SELECTORS) or safe_get_attribute(
                _first(quantity_locator) if quantity_locator is not None else row,
                "value",
            )
            variant_text = _extract_first_text(row, CART_ROW_VARIANT_SELECTORS)
            merchant_item_ref = safe_get_attribute(row, "data-sku") or safe_get_attribute(row, "data-item-id")
            item_id = merchant_item_ref or url or title or f"cart-item-{index}"
            cart_items.append(
                {
                    "item_id": item_id,
                    "title": title,
                    "price_text": price_text,
                    "quantity_text": quantity_text,
                    "variant_text": variant_text,
                    "url": url,
                    "merchant_item_ref": merchant_item_ref,
                }
            )
        if cart_items:
            break

    cart_item_count = count_from_subtotal
    if cart_item_count is None and row_count > 0:
        cart_item_count = row_count
    if cart_item_count is None and _contains_any(safe_body_text(page), CART_EMPTY_TEXT_MARKERS):
        cart_item_count = 0

    checkout_ready, checkout_notes = detect_checkout_entry_readiness(page)
    notes: list[str] = list(checkout_notes)
    total_text = _extract_first_text(page, CART_TOTAL_SELECTORS)
    if total_text:
        notes.append(f"cart_total_visible:{total_text}")
    if cart_item_count == 0:
        notes.append("cart_empty")
    if cart_item_count is None:
        notes.append("cart_count_unclear")
    return {
        "cart_items": cart_items,
        "cart_item_count": cart_item_count,
        "checkout_ready": checkout_ready,
        "notes": notes if notes else None,
    }


def remove_cart_item(
    page: Any,
    *,
    item_id: str | None = None,
    title: str | None = None,
) -> tuple[bool, list[str]]:
    notes: list[str] = []
    item_id_norm = _normalize_lower(item_id)
    title_norm = _normalize_lower(title)

    for attempt in range(2):
        for selector in CART_ROW_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            count = safe_count(locator)
            if count <= 0:
                continue

            for index in range(min(count, 12)):
                row = _nth(locator, index)
                row_item_id = _normalize_lower(
                    safe_get_attribute(row, "data-sku") or safe_get_attribute(row, "data-item-id")
                )
                row_title = _normalize_lower(_extract_first_text(row, CART_ROW_TITLE_SELECTORS))
                if item_id_norm and row_item_id != item_id_norm:
                    continue
                if title_norm and title_norm not in row_title:
                    continue
                if not item_id_norm and not title_norm and index > 0:
                    continue

                for remove_selector in CART_REMOVE_SELECTORS:
                    remove_locator = safe_locator(row, remove_selector)
                    if remove_locator is None or safe_count(remove_locator) <= 0:
                        continue
                    remove_target = _first(remove_locator)
                    if safe_click(remove_target):
                        remove_input_type = _normalize_lower(safe_get_attribute(remove_target, "type"))
                        if remove_input_type == "checkbox":
                            for update_selector in CART_UPDATE_SELECTORS:
                                update_locator = safe_locator(page, update_selector)
                                if update_locator is None or safe_count(update_locator) <= 0:
                                    continue
                                safe_click(_first(update_locator))
                                break
                        safe_wait_for_load(page)
                        notes.append(f"cart_item_removed:{remove_selector}:{index}")
                        return True, notes

                notes.append("cart_remove_control_not_found")
                return False, notes
        if attempt == 0:
            notes.extend(
                _run_stabilization_pass(
                    page,
                    anchor_selectors=CART_ANCHOR_SELECTORS,
                    wait_selectors=CART_ROW_SELECTORS,
                    note_prefix="cart_remove_ui_stabilization_retry",
                )
            )

    notes.append("cart_item_not_found")
    return False, notes


def update_cart_item_quantity(
    page: Any,
    *,
    item_id: str | None = None,
    title: str | None = None,
    quantity: int,
) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if quantity <= 0:
        notes.append("invalid_quantity")
        return False, notes

    item_id_norm = _normalize_lower(item_id)
    title_norm = _normalize_lower(title)

    for attempt in range(2):
        for selector in CART_ROW_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            count = safe_count(locator)
            if count <= 0:
                continue

            for index in range(min(count, 12)):
                row = _nth(locator, index)
                row_item_id = _normalize_lower(
                    safe_get_attribute(row, "data-sku") or safe_get_attribute(row, "data-item-id")
                )
                row_title = _normalize_lower(_extract_first_text(row, CART_ROW_TITLE_SELECTORS))
                if item_id_norm and row_item_id != item_id_norm:
                    continue
                if title_norm and title_norm not in row_title:
                    continue
                if not item_id_norm and not title_norm and index > 0:
                    continue

                for quantity_selector in CART_QUANTITY_SELECTORS:
                    quantity_locator = safe_locator(row, quantity_selector)
                    if quantity_locator is None or safe_count(quantity_locator) <= 0:
                        continue
                    target = _first(quantity_locator)
                    select_option_fn = getattr(target, "select_option", None)
                    if callable(select_option_fn):
                        try:
                            select_option_fn(str(quantity))
                            for update_selector in CART_UPDATE_SELECTORS:
                                update_locator = safe_locator(page, update_selector)
                                if update_locator is None or safe_count(update_locator) <= 0:
                                    continue
                                safe_click(_first(update_locator))
                                break
                            safe_wait_for_load(page)
                            notes.append(f"cart_quantity_updated:{quantity_selector}:{quantity}")
                            return True, notes
                        except Exception:
                            pass
                    if safe_fill(target, str(quantity)):
                        clicked_update = False
                        for update_selector in CART_UPDATE_SELECTORS:
                            update_locator = safe_locator(page, update_selector)
                            if update_locator is None or safe_count(update_locator) <= 0:
                                continue
                            clicked_update = safe_click(_first(update_locator))
                            if clicked_update:
                                break
                        if not clicked_update:
                            safe_press(target, "Enter")
                        safe_wait_for_load(page)
                        notes.append(f"cart_quantity_filled:{quantity_selector}:{quantity}")
                        return True, notes

                notes.append("cart_quantity_control_not_found")
                return False, notes
        if attempt == 0:
            notes.extend(
                _run_stabilization_pass(
                    page,
                    anchor_selectors=CART_ANCHOR_SELECTORS,
                    wait_selectors=CART_ROW_SELECTORS,
                    note_prefix="cart_quantity_ui_stabilization_retry",
                )
            )

    notes.append("cart_item_not_found")
    return False, notes


def extract_latest_order_evidence(page: Any) -> dict[str, Any]:
    current_url = safe_page_url(page)
    page_title = safe_page_title(page)
    notes: list[str] = []

    card = None
    for selector in ORDERS_CARD_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        card = _first(locator)
        notes.append(f"orders_card_detected:{selector}")
        break

    scope = card or page
    title = _extract_first_text(scope, ORDER_TITLE_SELECTORS)
    order_id_hint = safe_get_attribute(card, "data-order-id") if card is not None else None
    if not order_id_hint:
        order_id_hint = _extract_first_text(scope, ORDER_ID_SELECTORS)
    order_date_text = _extract_first_text(scope, ORDER_DATE_SELECTORS)
    shipping_stage_text = _extract_first_text(scope, ORDER_STATUS_SELECTORS)
    expected_delivery_text = _extract_first_text(scope, ORDER_ETA_SELECTORS)
    order_total_text = _extract_first_text(scope, ORDER_TOTAL_SELECTORS)
    returns_entry_hint = _extract_first_attr(scope, ORDER_RETURNS_LINK_SELECTORS, "href")
    support_entry_hint = _extract_first_attr(scope, ORDER_SUPPORT_LINK_SELECTORS, "href")
    if returns_entry_hint and returns_entry_hint.startswith("/"):
        returns_entry_hint = urljoin(BB_HOME_URL, returns_entry_hint)
    if support_entry_hint and support_entry_hint.startswith("/"):
        support_entry_hint = urljoin(BB_HOME_URL, support_entry_hint)

    if current_url and "order" not in _normalize_lower(current_url):
        notes.append("orders_url_not_confirmed")

    return {
        "order_id_hint": order_id_hint,
        "order_date_text": order_date_text,
        "shipping_stage_text": shipping_stage_text,
        "expected_delivery_text": expected_delivery_text,
        "order_total_text": order_total_text,
        "order_card_title": title,
        "orders_page_url": current_url,
        "support_entry_hint": support_entry_hint,
        "returns_entry_hint": returns_entry_hint,
        "notes": notes or None,
        "page_title": page_title,
    }


def attempt_cancel_latest_order(page: Any) -> dict[str, Any]:
    notes: list[str] = []
    current_url = safe_page_url(page)
    if current_url is None or "order" not in _normalize_lower(current_url):
        if not safe_goto(page, BB_ORDERS_URL):
            return {
                "cancelled": False,
                "cancellable": False,
                "order_card_title": None,
                "shipping_stage_text": None,
                "spoken_summary": "I could not open your orders page to attempt a cancellation.",
                "notes": "orders_navigation_failed",
            }
        notes.append("orders_page_opened_for_cancellation")

    evidence = extract_latest_order_evidence(page)
    order_title = _normalize_text(evidence.get("order_card_title")) or "your item"
    shipping_stage_text = _normalize_text(evidence.get("shipping_stage_text")) or None
    shipping_text_lower = _normalize_lower(shipping_stage_text)
    if any(token in shipping_text_lower for token in ("shipped", "out for delivery", "delivered", "dispatch")):
        notes.append("order_already_shipped")
        return {
            "cancelled": False,
            "cancellable": False,
            "order_card_title": order_title,
            "shipping_stage_text": shipping_stage_text,
            "spoken_summary": "This order cannot be cancelled as it has already shipped.",
            "notes": ", ".join(notes),
        }

    scope = page
    for selector in ORDERS_CARD_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        scope = _first(locator)
        notes.append(f"orders_card_detected_for_cancellation:{selector}")
        break

    clicked_cancel = False
    for selector in ORDER_CANCEL_ENTRY_SELECTORS:
        locator = safe_locator(scope, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        if safe_click(_first(locator)):
            safe_wait_for_load(page)
            notes.append(f"cancel_entry_clicked:{selector}")
            clicked_cancel = True
            break

    if not clicked_cancel:
        notes.append("cancel_entry_not_found")
        return {
            "cancelled": False,
            "cancellable": False,
            "order_card_title": order_title,
            "shipping_stage_text": shipping_stage_text,
            "spoken_summary": "This order cannot be cancelled as it has already shipped.",
            "notes": ", ".join(notes),
        }

    confirmed = False
    for selector in ORDER_CANCEL_CONFIRM_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None or safe_count(locator) <= 0:
            continue
        if safe_click(_first(locator)):
            safe_wait_for_load(page)
            notes.append(f"cancel_confirmation_clicked:{selector}")
            confirmed = True
            break

    if not confirmed:
        notes.append("cancel_confirmation_not_found")

    return {
        "cancelled": True,
        "cancellable": True,
        "order_card_title": order_title,
        "shipping_stage_text": shipping_stage_text,
        "spoken_summary": f"Your order for {order_title} has been cancelled.",
        "notes": ", ".join(notes),
    }


def infer_page_hints(
    *,
    observed_url: str | None,
    page_title: str | None,
    product_candidates: list[dict[str, Any]],
    primary_product: dict[str, Any] | None,
    cart_item_count: int | None,
    checkout_ready: bool | None,
) -> list[str]:
    hints: list[str] = []
    url = _normalize_lower(observed_url)
    path = _normalized_path(observed_url)
    title = _normalize_lower(page_title)

    if title == "access denied" or any(marker in title for marker in ACCESS_DENIED_TEXT_MARKERS):
        hints.extend(["access_denied", "unknown"])

    if "captcha" in url or "captcha" in title:
        hints.append("captcha")
    if "otp" in url or "otp" in title or "verification code" in title:
        hints.append("otp")
    if "login" in url or "login" in title or "sign in" in title:
        hints.append("login")
    if "customer/orders" in url or "order history" in title or "my orders" in title:
        hints.append("orders")
    if "checkoutasguest" in url or "checkout as guest" in title:
        hints.extend(["checkout", "guest_checkout_entry_visible"])
    elif checkout_ready is True or "checkout" in url or "checkout" in title:
        hints.append("checkout")
    if cart_item_count is not None or path == "/cart" or "shopping cart" in title or "cart" in title:
        hints.append("cart")
    if primary_product is not None or _is_probable_product_url(observed_url):
        hints.append("product_detail")
    if product_candidates or path == "/search" or "?q=" in url:
        hints.append("search_results")
    if "access_denied" not in hints and not hints and _is_demo_store_url(observed_url) and path in {"", "/"}:
        hints.append("home")
    if not hints:
        hints.append("unknown")

    deduped: list[str] = []
    for hint in hints:
        if hint not in deduped:
            deduped.append(hint)
    return deduped


def recover_to_stable_page(page: Any, *, preferred: str | None = None) -> dict[str, Any]:
    target_order: list[str] = []
    preferred_norm = _normalize_lower(preferred)
    if preferred_norm in {"home", "search", "cart"}:
        target_order.append(preferred_norm)
    for target in ["home", "search", "cart"]:
        if target not in target_order:
            target_order.append(target)

    target_urls = {
        "home": BB_HOME_URL,
        "search": f"{BB_HOME_URL}/search",
        "cart": BB_CART_URL,
    }

    notes: list[str] = []
    notes.extend(dismiss_common_interruptions(page))
    for target in target_order:
        url = target_urls[target]
        if safe_goto(page, url):
            return {
                "target": target,
                "success": True,
                "landed_url": safe_page_url(page),
                "notes": notes or None,
            }
        notes.append(f"recovery_failed:{target}")

    return {
        "target": target_order[0],
        "success": False,
        "landed_url": safe_page_url(page),
        "notes": notes or ["recovery_navigation_failed"],
    }
