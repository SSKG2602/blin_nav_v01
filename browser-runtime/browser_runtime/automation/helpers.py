from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urljoin
from uuid import UUID

logger = logging.getLogger(__name__)

BB_HOME_URL = "https://www.bigbasket.com"
BB_CART_URL = "https://www.bigbasket.com/basket/"
BB_ORDERS_URL = "https://www.bigbasket.com/order/order-history/"

AMAZON_HOME_URL = BB_HOME_URL
AMAZON_CART_URL = BB_CART_URL
AMAZON_ORDERS_URL = BB_ORDERS_URL

SEARCH_INPUT_SELECTORS = [
    "input[id='search']",
    "#autocomplete-search",
    "input[name='searchQuery']",
    "input[placeholder*='Search']",
    "input[placeholder*='search']",
    "input[type='search']",
]

SEARCH_RESULT_CONTAINER_SELECTOR = (
    "div.SKUDeck___StyledDiv, "
    "li.PaginateItems___StyledLi, "
    "div[class*='SKUDeck'], "
    "div[qa='product-listing'], "
    "li[class*='PaginateItems'], "
    "div[class*='product-card'], "
    "div[class*='ProductCard'], "
    "div[class*='sku-']"
)
SEARCH_RESULT_LINK_SELECTORS = [
    "a[href*='/pd/']",
    "div[class*='SKUDeck'] a",
    "li[class*='PaginateItems'] a",
]

CHECKOUT_BUTTON_SELECTORS = [
    "button[class*='Checkout']",
    "button[qa='checkout']",
    "a[href*='checkout']",
    "button[class*='Proceed']",
]

ADD_TO_CART_BUTTON_SELECTORS = [
    "button[class*='AddToCart']",
    "button[qa='add-to-cart']",
    "div[class*='AddToCart'] button",
    "button[class*='add-to-basket']",
    "button[class*='AddBtn']",
    "button[class*='add-btn']",
    "button:has-text('Add')",
    "button:has-text('ADD')",
]

VARIANT_OPTION_SELECTORS = [
    "button[class*='Variant']",
    "button[class*='Pack']",
    "div[class*='Variant'] button",
    "div[class*='PackSize'] button",
    "[role='button'][class*='Variant']",
]

CART_ROW_SELECTORS = [
    "div[class*='BasketItem']",
    "div[class*='basket-item']",
    "div[qa='basket-item']",
    "li[class*='BasketItem']",
]

CART_REMOVE_SELECTORS = [
    "button[class*='Remove']",
    "button[qa='remove-item']",
    "button[class*='Delete']",
    "button[aria-label*='Remove']",
]

CART_QUANTITY_SELECTORS = [
    "select[class*='Quantity']",
    "input[name*='qty']",
    "input[name*='quantity']",
    "input[class*='Quantity']",
]

ORDERS_CARD_SELECTORS = [
    "div[class*='OrderCard']",
    "div[class*='order-card']",
    "li[class*='OrderCard']",
    "div[qa='order-card']",
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
    "h1.product-name",
    "div[qa='product-name'] h1",
    "button[class*='AddToCart']",
]

CART_ANCHOR_SELECTORS = [
    "div[class*='BasketItem']",
    "div[qa='basket-item']",
    "button[class*='Checkout']",
]

CHECKOUT_ANCHOR_SELECTORS = [
    "button[class*='Checkout']",
    "button[qa='place-order']",
    "button[class*='PlaceOrder']",
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
    "div[class*='QuantityControl']",
    "div[class*='qty-']",
    "div[class*='CartCount']",
    "button[class*='CounterButton']",
    "div[class*='ItemCount']",
    "div[class*='counter']",
    "div[class*='Counter']",
    "button[class*='increase']",
    "button[class*='Increase']",
    "span[class*='CartCount']",
]

PRODUCT_TITLE_SELECTORS = [
    "h1.product-name",
    "span[class*='ProductName']",
    "h1[class*='ProductName']",
    "div[qa='product-name'] h1",
    "h1[class*='product']",
    "div[class*='product-title'] h1",
    "h1",
]

PRODUCT_PRICE_SELECTORS = [
    "span[class*='Pricing']",
    "div[class*='PriceContainer']",
    "span[qa='price']",
]

SEARCH_RESULT_TITLE_SELECTORS = [
    "div[qa='product-name']",
    "h3",
    "span[class*='ProductName']",
    "a[href*='/pd/']",
]

SEARCH_RESULT_PRICE_SELECTORS = [
    "span[class*='Pricing']",
    "div[class*='PriceContainer']",
    "span[qa='price']",
    "span[class*='price']",
]

PRODUCT_AVAILABILITY_SELECTORS = [
    "button[class*='AddToCart']",
    "button[qa='add-to-cart']",
    "span[class*='Stock']",
    "div[class*='Inventory']",
]

PRODUCT_VARIANT_VALUE_SELECTORS = [
    "div[class*='PackSize'] span",
    "span[class*='Pack']",
    "div[class*='Variant'] span",
    "div[qa='product-variant'] span",
]

PRODUCT_RATING_SELECTORS = [
    "span[class*='Rating']",
    "div[class*='Rating']",
    "span[qa='rating']",
]

PRODUCT_REVIEW_COUNT_SELECTORS = [
    "span[class*='ReviewCount']",
    "div[class*='ReviewCount']",
    "span[qa='review-count']",
]

PRODUCT_BRAND_SELECTORS = [
    "a[class*='Brand']",
    "div[class*='Brand']",
    "span[class*='Brand']",
    "div[qa='brand']",
]

PRODUCT_REVIEW_SNIPPET_SELECTORS = [
    "div[class*='Review'] p",
    "div[class*='Review'] span",
    "div[qa='review'] p",
    "div[qa='review'] span",
]

ACCESS_DENIED_TEXT_MARKERS = (
    "you don't have permission to access",
    "errors.edgesuite.net",
    "reference #",
)

CART_COUNT_SELECTORS = [
    "div[class*='BasketSummary']",
    "span[class*='ItemCount']",
    "div[qa='basket-count']",
    "span[class*='badge']",
    "span[class*='Badge']",
    "div[class*='CartCount']",
    "span[class*='CartCount']",
    "a[href*='basket'] span",
]

CART_ROW_TITLE_SELECTORS = [
    "div[class*='ProductName']",
    "div[qa='product-name']",
    "a[href*='/pd/']",
    "h3",
]

CART_ROW_LINK_SELECTORS = [
    "a[href*='/pd/']",
    "div[class*='ProductName'] a",
    "div[qa='product-name'] a",
    "h3 a[href]",
]

CART_ROW_PRICE_SELECTORS = [
    "span[class*='Pricing']",
    "div[class*='PriceContainer']",
    "span[qa='price']",
    "div[class*='price']",
]

CART_ROW_QUANTITY_TEXT_SELECTORS = [
    "span[class*='Quantity']",
    "div[class*='Quantity']",
    "input[name*='quantity']",
    "input[name*='qty']",
]

CART_ROW_VARIANT_SELECTORS = [
    "span[class*='Variant']",
    "span[class*='Pack']",
    "div[class*='PackSize']",
]

ORDER_TITLE_SELECTORS = [
    "div[class*='ProductName']",
    "a[href*='order']",
    "h4",
    "h5",
]

ORDER_ID_SELECTORS = [
    "span[class*='OrderId']",
    "div[class*='OrderId']",
    "bdi",
]

ORDER_DATE_SELECTORS = [
    "span[class*='OrderDate']",
    "div[class*='OrderDate']",
    "span[class*='Date']",
]

ORDER_STATUS_SELECTORS = [
    "span[class*='Status']",
    "div[class*='Status']",
    "span[class*='Delivery']",
]

ORDER_ETA_SELECTORS = [
    "span[class*='Delivery']",
    "div[class*='Delivery']",
    "span[class*='Eta']",
]

ORDER_TOTAL_SELECTORS = [
    "span[class*='Price']",
    "div[class*='Price']",
    "span[qa='price']",
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

_JUNK_LINK_TOKENS = ("help", "support", "sponsored", "login")
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
        if "/pd/" not in url_text:
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
    url_text = _normalize_lower(url)
    if not url_text:
        return False
    if "/ps/" not in url_text and "?q=" not in url_text:
        return False
    condensed = "+".join(part for part in query.split() if part)
    encoded = quote_plus(query)
    return condensed in url_text or encoded in url_text


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
    """Returns True if BigBasket is showing a location/pincode modal blocking the page."""
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


def classify_page_state(page: Any) -> str:
    """
    Classify the current browser page into a named state.
    Returns one of:
      'blank' | 'login' | 'checkout' | 'cart' | 'product' | 'search_results' | 'home' | 'unknown'
    This is used as a pre-action guard in route handlers.
    """
    url = _normalize_lower(safe_page_url(page))
    if not url or url == "about:blank":
        return "blank"
    if detect_access_denied(page):
        return "unknown"
    if "login" in url or "signin" in url or "sign-in" in url:
        return "login"
    if "checkout" in url:
        return "checkout"
    if "/basket/" in url or ("basket" in url and "bigbasket" not in url):
        return "cart"
    if "/bb-cart/" in url:
        return "cart"
    if "/pd/" in url:
        return "product"
    if "/ps/" in url or "?q=" in url or "search" in url:
        return "search_results"
    if "bigbasket.com" in url:
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

    fallback_url = f"https://www.bigbasket.com/ps/?q={query_text.replace(' ', '+')}"

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
            if safe_goto(page, fallback_url):
                notes.append("search_box_missing_used_url_fallback")
                return True, notes
            notes.append("search_box_not_found")
            return False, notes

        if not safe_fill(target, query_text, timeout_ms=1000):
            if safe_goto(page, fallback_url):
                notes.append("search_fill_failed_used_url_fallback")
                return True, notes
            notes.append("search_fill_failed")
            return False, notes
        if not safe_press(target, "Enter"):
            if safe_goto(page, fallback_url):
                notes.append("search_submit_failed_used_url_fallback")
                return True, notes
            notes.append("search_submit_failed")
            return False, notes
        safe_wait_for_load(page, timeout_ms=4000)
        return True, notes

    notes.append("search_submit_unresolved")
    return False, notes


def collect_search_result_candidates(page: Any, limit: int = 8) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    containers = safe_locator(page, SEARCH_RESULT_CONTAINER_SELECTOR)
    container_count = safe_count(containers) if containers is not None else 0

    for index in range(min(limit, container_count)):
        container = _nth(containers, index)
        title = _extract_first_text(container, SEARCH_RESULT_TITLE_SELECTORS)
        url = _extract_first_attr(container, ["a[href*='/pd/']", "a[href]"], "href")
        price = _extract_first_text(container, SEARCH_RESULT_PRICE_SELECTORS)
        rating = _extract_first_text(container, ["span[class*='Rating']", "span[qa='rating']"])
        review_count = _extract_first_text(
            container,
            ["span[class*='ReviewCount']", "span[qa='review-count']", "span[class*='Review']"],
        )
        availability = _extract_first_text(
            container,
            ["button[class*='AddToCart']", "span[class*='Stock']", "div[class*='Inventory']"],
        )

        if url and url.startswith("/"):
            url = urljoin(BB_HOME_URL, url)

        candidate = {
            "title": title,
            "price_text": price,
            "url": url,
            "rating_text": rating,
            "review_count_text": review_count,
            "availability_text": availability,
            "variant_text": None,
        }
        if any(value for value in candidate.values()):
            candidates.append(candidate)

    if candidates:
        return candidates

    for selector in SEARCH_RESULT_LINK_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        href = safe_get_attribute(_first(locator), "href")
        title = safe_inner_text(_first(locator))
        if href and href.startswith("/"):
            href = urljoin(BB_HOME_URL, href)
        if title or href:
            candidates.append(
                {
                    "title": title,
                    "price_text": None,
                    "url": href,
                    "rating_text": None,
                    "review_count_text": None,
                    "availability_text": None,
                    "variant_text": None,
                }
            )
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
        price = _normalize_text(candidate.get("price_text"))

        score = 0
        if title:
            score += 2
        if price:
            score += 1
        if "/pd/" in url:
            score += 6
        if "/ps/" in url:
            score -= 2
        if any(token in url for token in _JUNK_LINK_TOKENS):
            score -= 6
        if any(token in title for token in _JUNK_TITLE_TOKENS):
            score -= 4
        if not url:
            score -= 2
        if query_tokens:
            for token in query_tokens:
                if token in title:
                    score += 3
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
    variant_options = _extract_text_list(page, VARIANT_OPTION_SELECTORS, limit=10)
    review_snippets = _extract_text_list(page, PRODUCT_REVIEW_SNIPPET_SELECTORS, limit=4)
    evidence = {
        "title": _extract_first_text(page, PRODUCT_TITLE_SELECTORS),
        "price_text": _extract_first_text(page, PRODUCT_PRICE_SELECTORS),
        "availability_text": _extract_first_text(page, PRODUCT_AVAILABILITY_SELECTORS),
        "variant_text": _extract_first_text(page, PRODUCT_VARIANT_VALUE_SELECTORS),
        "rating_text": _extract_first_text(page, PRODUCT_RATING_SELECTORS),
        "review_count_text": _extract_first_text(page, PRODUCT_REVIEW_COUNT_SELECTORS),
        "brand_text": _extract_first_text(page, PRODUCT_BRAND_SELECTORS),
        "review_snippets": review_snippets,
        "variant_options": variant_options,
        "url": safe_page_url(page),
        "page_title": safe_page_title(page),
    }
    notes: list[str] = []
    if not evidence["title"]:
        notes.append("title_missing")
    if not evidence["price_text"]:
        notes.append("price_missing")
    if notes:
        evidence["notes"] = ", ".join(notes)
    else:
        evidence["notes"] = None
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

    for attempt in range(2):
        for selector in VARIANT_OPTION_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            count = safe_count(locator)
            if count <= 0:
                continue

            for index in range(min(count, 12)):
                option = _nth(locator, index)
                option_text = _normalize_lower(safe_inner_text(option))
                if not option_text:
                    continue
                if not any(hint.lower() in option_text for hint in hints):
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


def _verify_add_to_cart_evidence(page: Any, pre_count: int | None) -> bool:
    """
    Returns True if there is evidence the item was actually added to the cart.
    Evidence = cart badge count increased OR a quantity stepper appeared.
    """
    import time

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        post_count = _read_cart_badge_count(page)
        if post_count is not None:
            pre = pre_count if pre_count is not None else 0
            if post_count > pre:
                return True
        for selector in BB_QUANTITY_STEPPER_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is not None and safe_count(locator) > 0:
                if safe_is_visible(_first(locator)) is not False:
                    return True
        time.sleep(0.3)
    return False


def add_current_product_to_cart(page: Any, *, session_id: UUID) -> tuple[bool, list[str]]:
    notes: list[str] = []
    current_url = safe_page_url(page)
    if action_guard.should_skip_duplicate_add_to_cart(session_id, current_url=current_url):
        notes.append("duplicate_add_to_cart_skipped")
        return True, notes

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
                if _verify_add_to_cart_evidence(page, pre_count):
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
    url = _normalize_lower(safe_page_url(page))
    if "checkout" in url:
        notes.append("already_in_checkout_path")
        return True, notes

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
        ready, readiness_notes = detect_checkout_entry_readiness(page)
        notes.extend(readiness_notes)
        if ready is True:
            current_url = _normalize_lower(safe_page_url(page))
            if "checkout" in current_url:
                return True, notes
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
                    return True, notes
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
    count_from_subtotal = _parse_int(_extract_first_text(page, CART_COUNT_SELECTORS))
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

    checkout_ready, checkout_notes = detect_checkout_entry_readiness(page)
    notes: list[str] = list(checkout_notes)
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
                    if safe_click(_first(remove_locator)):
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
                            safe_wait_for_load(page)
                            notes.append(f"cart_quantity_updated:{quantity_selector}:{quantity}")
                            return True, notes
                        except Exception:
                            pass
                    if safe_fill(target, str(quantity)):
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
    title = _normalize_lower(page_title)

    if title == "access denied" or any(marker in title for marker in ACCESS_DENIED_TEXT_MARKERS):
        hints.extend(["access_denied", "unknown"])

    if "captcha" in url or "captcha" in title:
        hints.append("captcha")
    if "otp" in url or "otp" in title or "verification code" in title:
        hints.append("otp")
    if "login" in url or "login" in title or "sign in" in title:
        hints.append("login")
    if "order-history" in url or "order history" in title or "my orders" in title:
        hints.append("orders")
    if checkout_ready is True or "checkout" in url or "checkout" in title:
        hints.append("checkout")
    if cart_item_count is not None or "cart" in url or "cart" in title:
        hints.append("cart")
    if primary_product is not None or "/pd/" in url:
        hints.append("product_detail")
    if product_candidates or "/ps/" in url or "?q=" in url:
        hints.append("search_results")
    if "access_denied" not in hints and not hints and "bigbasket.com" in url:
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
        "search": f"{BB_HOME_URL}/ps/?q={quote_plus('dog food')}",
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
