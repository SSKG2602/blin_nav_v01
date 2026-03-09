from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urljoin
from uuid import UUID

logger = logging.getLogger(__name__)

AMAZON_HOME_URL = "https://www.amazon.in"
AMAZON_CART_URL = "https://www.amazon.in/gp/cart/view.html"
AMAZON_ORDERS_URL = "https://www.amazon.in/gp/css/order-history"

SEARCH_INPUT_SELECTORS = [
    "input#twotabsearchtextbox",
    "input[name='field-keywords']",
    "input[type='search']",
]

SEARCH_RESULT_CONTAINER_SELECTOR = '[data-component-type="s-search-result"]'
SEARCH_RESULT_LINK_SELECTORS = [
    '[data-component-type="s-search-result"] h2 a[href*="/dp/"]',
    '[data-component-type="s-search-result"] a[href*="/dp/"]',
    '[data-component-type="s-search-result"] h2 a[href]',
]

CHECKOUT_BUTTON_SELECTORS = [
    'input[name="proceedToRetailCheckout"]',
    "#sc-buy-box-ptc-button input[type='submit']",
    "#sc-buy-box-ptc-button a",
    'a[href*="/gp/buy/"]',
]

ADD_TO_CART_BUTTON_SELECTORS = [
    "#add-to-cart-button",
    "input#add-to-cart-button",
    'input[name="submit.add-to-cart"]',
    '[data-action="add-to-cart"] input[type="submit"]',
]

VARIANT_OPTION_SELECTORS = [
    "#twister .a-button-text",
    "#twister li",
    "#variation_size_name li",
    "#variation_color_name li",
    "#variation_style_name li",
    "#twister-plus-inline-twister [role='button']",
]

CART_ROW_SELECTORS = [
    "div.sc-list-item-content",
    ".sc-list-item",
    '[data-name="Active Items"] .sc-list-item-content',
]

CART_REMOVE_SELECTORS = [
    'input[value="Delete"]',
    '[data-action="delete"] input[type="submit"]',
    '[data-action="delete"]',
    "button.sc-action-delete",
]

CART_QUANTITY_SELECTORS = [
    "select[name*='quantity']",
    "select.sc-update-quantity",
    "input[name='quantityBox']",
]

ORDERS_CARD_SELECTORS = [
    "[data-order-id]",
    ".order-card",
    ".a-box-group",
    ".order",
]

ORDER_CANCEL_ENTRY_SELECTORS = [
    "a[href*='cancel']",
    "input[value*='Cancel']",
    "button:has-text('Cancel')",
    "text=Cancel items",
    "text=Cancel order",
]

ORDER_CANCEL_CONFIRM_SELECTORS = [
    "input[value*='Cancel selected items']",
    "input[value*='Confirm cancellation']",
    "button:has-text('Confirm cancellation')",
    "button:has-text('Cancel selected items')",
    "text=Confirm cancellation",
    "text=Cancel selected items",
]

CAPTCHA_SELECTORS = [
    "input#captchacharacters",
    "img[src*='captcha']",
    "form[action*='validateCaptcha']",
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
    "#productTitle",
    "#add-to-cart-button",
    "#acrPopover",
]

CART_ANCHOR_SELECTORS = [
    "#sc-subtotal-label-buybox",
    ".sc-list-item",
    'input[name="proceedToRetailCheckout"]',
]

CHECKOUT_ANCHOR_SELECTORS = [
    "#submitOrderButtonId",
    "#placeYourOrder",
    "input[name='placeYourOrder1']",
]

MODAL_DISMISS_SELECTORS = [
    "#sp-cc-accept",
    "button#sp-cc-accept",
    "button[aria-label='Close']",
    "button.a-popover-close",
    "input[data-action-type='DISMISS']",
    "button[data-action='a-popover-close']",
]

_JUNK_LINK_TOKENS = ("slredirect", "/gp/help", "/customer-preferences", "sponsored")
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
        if "/dp/" not in url_text:
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
        if "checkout" in url_text or "/gp/buy/" in url_text:
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
    if "/s?" not in url_text and "field-keywords=" not in url_text:
        return False
    condensed = "+".join(part for part in query.split() if part)
    encoded = quote_plus(query)
    return condensed in url_text or encoded in url_text


def dismiss_common_interruptions(page: Any) -> list[str]:
    notes: list[str] = []
    for selector in MODAL_DISMISS_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        target = _first(locator)
        visible = safe_is_visible(target)
        if visible is False:
            continue
        if safe_click(target):
            notes.append(f"dismissed:{selector}")
    return notes


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

    for attempt in range(2):
        target = None
        for selector in SEARCH_INPUT_SELECTORS:
            safe_wait_for_selector(page, selector, timeout_ms=3500)
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            candidate = _first(locator)
            visible = safe_is_visible(candidate)
            if visible is False:
                continue
            target = candidate
            break

        if target is None:
            if attempt == 0 and safe_goto(page, AMAZON_HOME_URL):
                notes.append("search_context_reset")
                continue
            notes.append("search_box_not_found")
            return False, notes

        if not safe_fill(target, query_text):
            notes.append("search_fill_failed")
            return False, notes
        if not safe_press(target, "Enter"):
            notes.append("search_submit_failed")
            return False, notes
        safe_wait_for_load(page)
        return True, notes

    notes.append("search_submit_unresolved")
    return False, notes


def collect_search_result_candidates(page: Any, limit: int = 8) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    containers = safe_locator(page, SEARCH_RESULT_CONTAINER_SELECTOR)
    container_count = safe_count(containers) if containers is not None else 0

    for index in range(min(limit, container_count)):
        container = _nth(containers, index)
        title = _extract_first_text(container, ["h2 a span", "h2 span", "a h2 span", "span.a-size-medium"])
        url = _extract_first_attr(container, ["h2 a[href]", "a[href*='/dp/']", "a[href]"], "href")
        price = _extract_first_text(
            container,
            ["span.a-price span.a-offscreen", "span.a-price-whole", ".a-price .a-offscreen"],
        )
        rating = _extract_first_text(container, ["span.a-icon-alt"])
        review_count = _extract_first_text(container, ["span[aria-label*='ratings']", "span.a-size-base.s-underline-text"])
        availability = _extract_first_text(container, ["span.a-color-success", "span.a-color-price"])

        if url and url.startswith("/"):
            url = urljoin(AMAZON_HOME_URL, url)

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
            href = urljoin(AMAZON_HOME_URL, href)
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


def choose_best_product_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = -10_000

    for candidate in candidates:
        url = _normalize_lower(candidate.get("url"))
        title = _normalize_lower(candidate.get("title"))
        price = _normalize_text(candidate.get("price_text"))

        score = 0
        if title:
            score += 2
        if price:
            score += 1
        if "/dp/" in url:
            score += 6
        if "/gp/product/" in url:
            score += 4
        if any(token in url for token in _JUNK_LINK_TOKENS):
            score -= 6
        if any(token in title for token in _JUNK_TITLE_TOKENS):
            score -= 4
        if not url:
            score -= 2

        if score > best_score:
            best_score = score
            best = candidate

    if best is None or best_score <= 0:
        return None
    return best


def open_best_search_result(page: Any, *, session_id: UUID) -> tuple[bool, dict[str, Any] | None, list[str]]:
    notes: list[str] = []
    current_url = safe_page_url(page)
    if action_guard.should_skip_duplicate_product_open(session_id, current_url=current_url):
        notes.append("duplicate_product_open_skipped")
        return False, None, notes

    candidates = collect_search_result_candidates(page)
    candidate = choose_best_product_candidate(candidates)
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
    review_snippets = _extract_text_list(
        page,
        [
            "#cm-cr-dp-review-list [data-hook='review-collapsed'] span",
            "#cm-cr-dp-review-list [data-hook='review-body'] span",
            "[data-hook='review-collapsed'] span",
            "[data-hook='review-body'] span",
        ],
        limit=4,
    )
    evidence = {
        "title": _extract_first_text(page, ["#productTitle", "span#productTitle", "h1.a-size-large span"]),
        "price_text": _extract_first_text(
            page,
            ["span.a-price span.a-offscreen", "#corePrice_feature_div span.a-offscreen", "span.a-price-whole"],
        ),
        "availability_text": _extract_first_text(page, ["#availability span", "#availability .a-color-success"]),
        "variant_text": _extract_first_text(
            page,
            ["#variation_size_name .selection", "#variation_color_name .selection", "#inline-twister-expanded-dimension-text-color_name"],
        ),
        "rating_text": _extract_first_text(page, ["#acrPopover span.a-icon-alt", "span[data-hook='rating-out-of-text']"]),
        "review_count_text": _extract_first_text(page, ["#acrCustomerReviewText", "span[data-hook='total-review-count']"]),
        "brand_text": _extract_first_text(page, ["#bylineInfo", "a#bylineInfo", "tr.po-brand td.a-span9 span"]),
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


def add_current_product_to_cart(page: Any, *, session_id: UUID) -> tuple[bool, list[str]]:
    notes: list[str] = []
    current_url = safe_page_url(page)
    if action_guard.should_skip_duplicate_add_to_cart(session_id, current_url=current_url):
        notes.append("duplicate_add_to_cart_skipped")
        return True, notes

    for attempt in range(2):
        for selector in ADD_TO_CART_BUTTON_SELECTORS:
            locator = safe_locator(page, selector)
            if locator is None:
                continue
            if safe_count(locator) <= 0:
                continue
            target = _first(locator)
            visible = safe_is_visible(target)
            if visible is False:
                continue
            if not safe_click(target):
                continue
            safe_wait_for_load(page)
            action_guard.record_add_to_cart(session_id, current_url=safe_page_url(page))
            notes.append(f"add_to_cart_clicked:{selector}")
            return True, notes
        if attempt == 0:
            notes.extend(
                _run_stabilization_pass(
                    page,
                    anchor_selectors=PRODUCT_ANCHOR_SELECTORS,
                    wait_selectors=ADD_TO_CART_BUTTON_SELECTORS,
                    note_prefix="add_to_cart_ui_stabilization_retry",
                )
            )

    notes.append("add_to_cart_button_not_found")
    return False, notes


def detect_checkout_entry_readiness(page: Any) -> tuple[bool | None, list[str]]:
    notes: list[str] = []
    url = _normalize_lower(safe_page_url(page))
    if "checkout" in url or "/gp/buy/" in url:
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
            if "checkout" in current_url or "/gp/buy/" in current_url:
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
    count_from_subtotal = _parse_int(
        _extract_first_text(page, ["#sc-subtotal-label-buybox", ".sc-subtotal-label-activecart"])
    )
    row_count = 0
    for selector in CART_ROW_SELECTORS:
        locator = safe_locator(page, selector)
        if locator is None:
            continue
        count = safe_count(locator)
        row_count = max(row_count, count)
        for index in range(min(count, 12)):
            row = _nth(locator, index)
            title = _extract_first_text(
                row,
                ["span.a-truncate-cut", ".sc-product-title", "a.sc-product-link", "h4 a"],
            )
            url = _extract_first_attr(
                row,
                ["a.sc-product-link", "a[href*='/dp/']", "h4 a[href]"],
                "href",
            )
            if url and url.startswith("/"):
                url = urljoin(AMAZON_HOME_URL, url)
            price_text = _extract_first_text(
                row,
                ["span.sc-product-price", "span.a-offscreen", ".sc-price"],
            )
            quantity_text = _extract_first_text(
                row,
                ["span.a-dropdown-prompt", "span.sc-product-quantity", "input[name='quantityBox']"],
            ) or safe_get_attribute(_first(safe_locator(row, "input[name='quantityBox']")) if safe_locator(row, "input[name='quantityBox']") is not None else row, "value")
            variant_text = _extract_first_text(
                row,
                [".sc-product-variation", "span.a-size-small", ".a-color-secondary"],
            )
            merchant_item_ref = safe_get_attribute(row, "data-asin") or safe_get_attribute(row, "data-itemid")
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
                row_item_id = _normalize_lower(safe_get_attribute(row, "data-asin") or safe_get_attribute(row, "data-itemid"))
                row_title = _normalize_lower(
                    _extract_first_text(
                        row,
                        ["span.a-truncate-cut", ".sc-product-title", "a.sc-product-link", "h4 a"],
                    )
                )
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
                row_item_id = _normalize_lower(safe_get_attribute(row, "data-asin") or safe_get_attribute(row, "data-itemid"))
                row_title = _normalize_lower(
                    _extract_first_text(
                        row,
                        ["span.a-truncate-cut", ".sc-product-title", "a.sc-product-link", "h4 a"],
                    )
                )
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
    title = _extract_first_text(
        scope,
        [
            "a[href*='order-details']",
            "span.a-truncate-cut",
            ".yohtmlc-product-title",
            "h5 a",
        ],
    )
    order_id_hint = safe_get_attribute(card, "data-order-id") if card is not None else None
    if not order_id_hint:
        order_id_hint = _extract_first_text(scope, ["span.order-id", "bdi", ".a-color-secondary"])
    order_date_text = _extract_first_text(
        scope,
        ["span.order-info .a-color-secondary", ".order-date-invoice-item", ".a-color-secondary"],
    )
    shipping_stage_text = _extract_first_text(
        scope,
        [".shipment-progress-text", ".a-color-success", ".delivery-status", ".a-text-bold"],
    )
    expected_delivery_text = _extract_first_text(
        scope,
        [".js-delivery-text", ".a-color-base", ".delivery-box__primary-text"],
    )
    order_total_text = _extract_first_text(
        scope,
        [".a-color-price", ".order-total", ".grand-total-price"],
    )
    returns_entry_hint = _extract_first_attr(
        scope,
        ["a[href*='returns']", "a[href*='return']", "a[href*='contact-us']"],
        "href",
    )
    support_entry_hint = _extract_first_attr(
        scope,
        ["a[href*='contact-us']", "a[href*='help']", "a[href*='support']"],
        "href",
    )
    if returns_entry_hint and returns_entry_hint.startswith("/"):
        returns_entry_hint = urljoin(AMAZON_HOME_URL, returns_entry_hint)
    if support_entry_hint and support_entry_hint.startswith("/"):
        support_entry_hint = urljoin(AMAZON_HOME_URL, support_entry_hint)

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
        if not safe_goto(page, AMAZON_ORDERS_URL):
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

    if "captcha" in url or "captcha" in title:
        hints.append("captcha")
    if "otp" in url or "otp" in title or "verification code" in title:
        hints.append("otp")
    if "order-history" in url or "your orders" in title:
        hints.append("orders")
    if checkout_ready is True or "checkout" in url or "checkout" in title or "/gp/buy/" in url:
        hints.append("checkout")
    if cart_item_count is not None or "cart" in url or "cart" in title:
        hints.append("cart")
    if primary_product is not None or "/dp/" in url or "/gp/product/" in url:
        hints.append("product_detail")
    if product_candidates or "/s?" in url:
        hints.append("search_results")
    if not hints and "amazon.in" in url:
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
        "home": AMAZON_HOME_URL,
        "search": f"{AMAZON_HOME_URL}/s?k={quote_plus('dog food')}",
        "cart": AMAZON_CART_URL,
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
