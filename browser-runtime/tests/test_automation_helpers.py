from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from browser_runtime.automation.helpers import (
    action_guard,
    add_current_product_to_cart,
    attempt_checkout_entry,
    choose_best_product_candidate,
    classify_page_state,
    collect_search_result_candidates,
    collect_semantic_page_signals,
    detect_access_denied,
    detect_checkout_entry_readiness,
    dismiss_common_interruptions,
    extract_cart_evidence,
    extract_product_detail_evidence,
    recover_to_stable_page,
    select_variant_option,
    submit_search_query,
)


class FakeLocator:
    def __init__(self, entries: list[dict[str, Any]] | None = None):
        self._entries = entries or []

    @property
    def first(self) -> FakeLocator:
        if not self._entries:
            return FakeLocator([{}])
        return FakeLocator([self._entries[0]])

    def nth(self, index: int) -> FakeLocator:
        if not self._entries:
            return FakeLocator([{}])
        if index < 0 or index >= len(self._entries):
            return FakeLocator([{}])
        return FakeLocator([self._entries[index]])

    def count(self) -> int:
        return len(self._entries)

    def inner_text(self, timeout: int | None = None) -> str:
        if not self._entries:
            return ""
        return str(self._entries[0].get("text", ""))

    def get_attribute(self, attr_name: str, timeout: int | None = None) -> str | None:
        if not self._entries:
            return None
        attrs = self._entries[0].get("attrs", {})
        if isinstance(attrs, dict):
            value = attrs.get(attr_name)
            return None if value is None else str(value)
        return None

    def is_visible(self, timeout: int | None = None) -> bool:
        if not self._entries:
            return False
        return bool(self._entries[0].get("visible", False))

    def is_checked(self) -> bool:
        if not self._entries:
            return False
        attrs = self._entries[0].get("attrs", {})
        if isinstance(attrs, dict) and attrs.get("checked") is not None:
            return bool(attrs.get("checked"))
        return bool(self._entries[0].get("checked", False))

    def click(self, timeout: int | None = None) -> None:
        if not self._entries:
            return
        entry = self._entries[0]
        entry["clicked"] = True
        attrs = entry.setdefault("attrs", {})
        if attrs.get("type") in {"checkbox", "radio"}:
            attrs["checked"] = True
        on_click = entry.get("on_click")
        if callable(on_click):
            on_click()

    def fill(self, value: str, timeout: int | None = None) -> None:
        if self._entries:
            self._entries[0]["filled"] = value
            self._entries[0].setdefault("attrs", {})["value"] = value

    def press(self, key: str) -> None:
        if self._entries:
            self._entries[0]["pressed"] = key
            on_press = self._entries[0].get("on_press")
            if callable(on_press):
                on_press(key)

    def select_option(self, value: str) -> None:
        if not self._entries:
            raise RuntimeError("no option control")
        entry = self._entries[0]
        entry["selected_option"] = value
        entry.setdefault("attrs", {})["value"] = value
        nested = entry.setdefault("nested", {})
        options = nested.get("option", [])
        selected_options: list[dict[str, Any]] = []
        for option in options:
            attrs = option.setdefault("attrs", {})
            if str(attrs.get("value")) == str(value) or option.get("text") == value:
                attrs["selected"] = "selected"
                selected_options = [option]
            else:
                attrs.pop("selected", None)
        if selected_options:
            nested["option:checked"] = selected_options
            nested["option[selected]"] = selected_options

    def locator(self, selector: str) -> FakeLocator:
        if not self._entries:
            return FakeLocator([])
        nested = self._entries[0].get("nested", {})
        if isinstance(nested, dict):
            entry = nested.get(selector)
            if isinstance(entry, list):
                return FakeLocator(entry)
            if isinstance(entry, dict):
                return FakeLocator([entry])
        return FakeLocator([])


class FakePage:
    def __init__(
        self,
        *,
        url: str = "https://demo.nopcommerce.com",
        title: str = "Demo Store",
        selectors: dict[str, list[dict[str, Any]]] | None = None,
        fail_locator: bool = False,
        fail_goto: bool = False,
    ) -> None:
        self.url = url
        self._title = title
        self._selectors = selectors or {}
        self._fail_locator = fail_locator
        self._fail_goto = fail_goto

    def title(self) -> str:
        return self._title

    def locator(self, selector: str) -> FakeLocator:
        if self._fail_locator:
            raise RuntimeError("locator unavailable")
        return FakeLocator(self._selectors.get(selector, []))

    def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 15000) -> None:
        if self._fail_goto:
            raise RuntimeError("goto failed")
        self.url = url

    def wait_for_load_state(self, state: str = "domcontentloaded", timeout: int = 10000) -> None:
        return None

    def wait_for_selector(self, selector: str, timeout: int = 4000) -> None:
        if selector not in self._selectors:
            raise RuntimeError("selector unavailable")


def test_choose_best_product_candidate_prefers_real_nopcommerce_product_slug() -> None:
    candidates = [
        {
            "title": "Help",
            "url": "https://demo.nopcommerce.com/help",
            "price_text": None,
        },
        {
            "title": "Cell phones",
            "url": "https://demo.nopcommerce.com/cell-phones",
            "price_text": None,
        },
        {
            "title": "HTC One M8 Android L 5.0 Lollipop",
            "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
            "price_text": "$245.00",
        },
    ]

    chosen = choose_best_product_candidate(candidates, query="htc android phone")

    assert chosen is not None
    assert chosen["url"] == "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop"


def test_classify_page_state_recognizes_nopcommerce_surfaces() -> None:
    home = FakePage(
        url="https://demo.nopcommerce.com/",
        title="nopCommerce demo store",
        selectors={
            ".home-page": [{"visible": True}],
            "body": [{"text": "Welcome to our store", "visible": True}],
        },
    )
    listing = FakePage(
        url="https://demo.nopcommerce.com/cell-phones",
        title="Cell phones",
        selectors={
            ".product-grid .item-box": [{"visible": True}],
            "body": [{"text": "Cell phones HTC Nokia", "visible": True}],
        },
    )
    product = FakePage(
        url="https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        title="HTC One M8 Android L 5.0 Lollipop",
        selectors={
            "div.product-essential": [{"visible": True}],
            "button[id^='add-to-cart-button-']": [{"visible": True, "text": "Add to cart"}],
        },
    )
    cart = FakePage(
        url="https://demo.nopcommerce.com/cart",
        title="Shopping cart",
        selectors={
            ".shopping-cart-page": [{"visible": True}],
            "#checkout": [{"visible": True, "text": "Checkout"}],
        },
    )
    checkout = FakePage(
        url="https://demo.nopcommerce.com/login/checkoutasguest",
        title="Welcome, Please Sign In!",
        selectors={
            ".checkout-as-guest-button": [{"visible": True, "text": "Checkout as Guest"}],
        },
    )

    assert classify_page_state(home) == "home"
    assert classify_page_state(listing) == "search_results"
    assert classify_page_state(product) == "product"
    assert classify_page_state(cart) == "cart"
    assert classify_page_state(checkout) == "checkout"


def test_submit_search_query_uses_small_searchterms_and_button() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/",
        selectors={
            "#small-searchterms": [{"visible": True}],
            "button.search-box-button": [
                {
                    "visible": True,
                    "text": "Search",
                    "on_click": lambda: setattr(
                        page,
                        "url",
                        "https://demo.nopcommerce.com/search?q=htc",
                    ),
                }
            ],
            ".home-page": [{"visible": True}],
            "body": [{"text": "Welcome to our store", "visible": True}],
        },
    )

    submitted, notes = submit_search_query(page, "htc")

    assert submitted is True
    assert notes == []
    assert page.locator("#small-searchterms").first.get_attribute("value") == "htc"
    assert page.url.endswith("/search?q=htc")


def test_submit_search_query_halts_on_blocking_modal() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/",
        selectors={
            "div[class*='LocationModal']": [{"visible": True}],
            "#small-searchterms": [{"visible": True}],
            "body": [{"text": "Welcome to our store", "visible": True}],
        },
    )

    submitted, notes = submit_search_query(page, "htc")

    assert submitted is False
    assert "location_blocked" in notes
    assert page.url == "https://demo.nopcommerce.com/"


def test_submit_search_query_halts_when_search_box_missing() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/",
        selectors={
            ".home-page": [{"visible": True}],
            "body": [{"text": "Welcome to our store", "visible": True}],
        },
    )

    submitted, notes = submit_search_query(page, "htc")

    assert submitted is False
    assert notes == ["search_box_not_found"]


def test_collect_search_result_candidates_reads_nopcommerce_cards() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/search?q=htc",
        title="Search",
        selectors={
            ".item-grid .item-box": [
                {
                    "visible": True,
                    "nested": {
                        ".product-title a": {
                            "text": "HTC One M8 Android L 5.0 Lollipop",
                            "attrs": {"href": "/htc-one-m8-android-l-50-lollipop"},
                        },
                        ".prices .actual-price": {"text": "$245.00"},
                        ".description": {"text": "HTC's latest smartphone for Android lovers."},
                        ".add-to-cart-button": {"text": "Add to cart"},
                    },
                },
                {
                    "visible": True,
                    "nested": {
                        ".product-title a": {
                            "text": "Nokia Lumia 1020",
                            "attrs": {"href": "/nokia-lumia-1020"},
                        },
                        ".prices .actual-price": {"text": "$349.00"},
                    },
                },
            ]
        },
    )

    candidates = collect_search_result_candidates(page, limit=4)

    assert len(candidates) == 2
    assert candidates[0]["title"] == "HTC One M8 Android L 5.0 Lollipop"
    assert candidates[0]["url"] == "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop"
    assert candidates[0]["summary_text"] == "HTC's latest smartphone for Android lovers."
    assert candidates[0]["availability_text"] == "Add to cart"


def test_extract_product_detail_evidence_for_simple_nopcommerce_product() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        title="HTC One M8 Android L 5.0 Lollipop",
        selectors={
            "div.product-name h1": [{"text": "HTC One M8 Android L 5.0 Lollipop", "visible": True}],
            ".prices .actual-price": [{"text": "$245.00", "visible": True}],
            ".overview .short-description": [
                {"text": "A lightweight Android handset with a bright screen.", "visible": True}
            ],
            "input[id*='EnteredQuantity']": [{"visible": True, "attrs": {"value": "1", "min": "1"}}],
            "button[id^='add-to-cart-button-']": [{"visible": True, "text": "Add to cart"}],
        },
    )

    evidence = extract_product_detail_evidence(page)

    assert evidence["title"] == "HTC One M8 Android L 5.0 Lollipop"
    assert evidence["price_text"] == "$245.00"
    assert evidence["summary_text"] == "A lightweight Android handset with a bright screen."
    assert evidence["quantity_text"] == "Qty: 1"
    assert evidence["availability_text"] == "Add to cart"
    assert evidence["blocker_hints"] == []
    assert evidence["notes"] is None


def test_extract_product_detail_evidence_flags_required_options() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/build-your-own-computer",
        title="Build your own computer",
        selectors={
            "div.product-name h1": [{"text": "Build your own computer", "visible": True}],
            ".prices .actual-price": [{"text": "$1,200.00", "visible": True}],
            ".attributes label.text-prompt": [{"text": "Processor *", "visible": True}],
            "select[id^='product_attribute_']": [
                {
                    "visible": True,
                    "attrs": {"value": "0"},
                    "nested": {
                        "option": [
                            {"text": "Please select", "attrs": {"value": "0", "selected": "selected"}},
                            {"text": "2.2 GHz Intel Pentium Dual-Core E2200", "attrs": {"value": "1"}},
                        ],
                        "option:checked": [
                            {"text": "Please select", "attrs": {"value": "0", "selected": "selected"}}
                        ],
                        "option[selected]": [
                            {"text": "Please select", "attrs": {"value": "0", "selected": "selected"}}
                        ],
                    },
                }
            ],
            "button[id^='add-to-cart-button-']": [{"visible": True, "text": "Add to cart"}],
        },
    )

    evidence = extract_product_detail_evidence(page)

    assert "option_selection_required" in evidence["blocker_hints"]
    assert "required_options:Processor *" in (evidence["notes"] or "")


def test_select_variant_option_supports_select_controls_and_duplicate_guard() -> None:
    action_guard.clear()
    session_id = uuid4()
    page = FakePage(
        url="https://demo.nopcommerce.com/build-your-own-computer",
        selectors={
            "select[id^='product_attribute_']": [
                {
                    "visible": True,
                    "attrs": {"value": "0"},
                    "nested": {
                        "option": [
                            {"text": "Please select", "attrs": {"value": "0"}},
                            {"text": "320 GB", "attrs": {"value": "4"}},
                        ]
                    },
                }
            ]
        },
    )

    selected, notes, signature = select_variant_option(
        page,
        session_id=session_id,
        variant_hint="320 GB",
    )
    assert selected is True
    assert signature == "320 gb"
    assert any("variant_selected:select" in note for note in notes)

    selected_again, notes_again, _ = select_variant_option(
        page,
        session_id=session_id,
        variant_hint="320 GB",
    )
    assert selected_again is True
    assert "duplicate_variant_selection_skipped" in notes_again


def test_add_to_cart_verifies_with_notification_and_duplicate_guard() -> None:
    action_guard.clear()
    session_id = uuid4()
    page = FakePage(
        url="https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
        selectors={
            "div.product-essential": [{"visible": True}],
            "div.product-name h1": [{"text": "HTC One M8 Android L 5.0 Lollipop", "visible": True}],
            ".prices .actual-price": [{"text": "$245.00", "visible": True}],
            "input[id*='EnteredQuantity']": [{"visible": True, "attrs": {"value": "1", "min": "1"}}],
            "#topcartlink .cart-qty": [{"text": "(0)", "visible": True}],
            "button[id^='add-to-cart-button-']": [
                {
                    "visible": True,
                    "text": "Add to cart",
                    "on_click": lambda: page._selectors.update(
                        {
                            ".bar-notification.success .content": [
                                {
                                    "visible": True,
                                    "text": "The product has been added to your shopping cart",
                                }
                            ],
                            "#topcartlink .cart-qty": [{"text": "(1)", "visible": True}],
                        }
                    ),
                }
            ],
        },
    )

    added, notes = add_current_product_to_cart(page, session_id=session_id)
    assert added is True
    assert "success_notification_visible" in notes
    assert any("add_to_cart_verified" in note for note in notes)

    added_again, notes_again = add_current_product_to_cart(page, session_id=session_id)
    assert added_again is True
    assert "duplicate_add_to_cart_skipped" in notes_again


def test_add_to_cart_blocks_minimum_quantity_product() -> None:
    action_guard.clear()
    session_id = uuid4()
    page = FakePage(
        url="https://demo.nopcommerce.com/sample-product",
        selectors={
            "div.product-essential": [{"visible": True}],
            "div.product-name h1": [{"text": "Sample product", "visible": True}],
            ".prices .actual-price": [{"text": "$19.00", "visible": True}],
            "input[id*='EnteredQuantity']": [{"visible": True, "attrs": {"value": "1", "min": "2"}}],
            "button[id^='add-to-cart-button-']": [{"visible": True, "text": "Add to cart"}],
        },
    )

    added, notes = add_current_product_to_cart(page, session_id=session_id)

    assert added is False
    assert "minimum_quantity_required" in notes
    assert "minimum_quantity_required:2" in notes
    assert page._selectors["input[id*='EnteredQuantity']"][0]["attrs"]["value"] == "1"
    assert "filled" not in page._selectors["input[id*='EnteredQuantity']"][0]


def test_extract_cart_evidence_reads_rows_and_checkout_readiness() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/cart",
        title="Shopping cart",
        selectors={
            "#topcartlink .cart-qty": [{"text": "(1)", "visible": True}],
            "tr.cart-item-row": [
                {
                    "attrs": {"data-item-id": "item-1"},
                    "nested": {
                        "td.product a": {
                            "text": "HTC One M8 Android L 5.0 Lollipop",
                            "attrs": {"href": "/htc-one-m8-android-l-50-lollipop"},
                        },
                        "td.subtotal span": {"text": "$245.00"},
                        "input.qty-input": {"attrs": {"value": "1"}},
                        ".attributes": {"text": "Color: Silver"},
                    },
                }
            ],
            "#checkout": [{"visible": True, "text": "Checkout"}],
            "#termsofservice": [{"visible": True, "attrs": {"type": "checkbox"}}],
            ".cart-total .value-summary strong": [{"text": "$245.00", "visible": True}],
        },
    )

    evidence = extract_cart_evidence(page)

    assert evidence["cart_item_count"] == 1
    assert evidence["checkout_ready"] is True
    assert evidence["cart_items"][0]["title"] == "HTC One M8 Android L 5.0 Lollipop"
    assert evidence["cart_items"][0]["quantity_text"] == "1"
    assert "terms_of_service_required" in (evidence["notes"] or [])
    assert "cart_total_visible:$245.00" in (evidence["notes"] or [])


def test_attempt_checkout_entry_checks_terms_and_stops_at_guest_entry() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/cart",
        title="Shopping cart",
        selectors={
            ".shopping-cart-page": [{"visible": True}],
            "#termsofservice": [{"visible": True, "attrs": {"type": "checkbox"}}],
            "#checkout": [
                {
                    "visible": True,
                    "text": "Checkout",
                    "on_click": lambda: (
                        setattr(page, "url", "https://demo.nopcommerce.com/login/checkoutasguest"),
                        page._selectors.update(
                            {
                                ".checkout-as-guest-button": [
                                    {"visible": True, "text": "Checkout as Guest"}
                                ],
                                "body": [
                                    {
                                        "visible": True,
                                        "text": "Welcome, please sign in or checkout as guest",
                                    }
                                ],
                            }
                        ),
                    ),
                }
            ],
        },
    )

    initiated, notes = attempt_checkout_entry(page)

    assert initiated is True
    assert "terms_of_service_checked" in notes
    assert "guest_checkout_entry_visible" in notes
    assert page.url.endswith("/login/checkoutasguest")
    assert page._selectors[".checkout-as-guest-button"][0].get("clicked") is not True


def test_detect_checkout_entry_readiness_reports_cart_empty() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/cart",
        title="Shopping cart",
        selectors={
            "body": [{"text": "Your shopping cart is empty!", "visible": True}],
        },
    )

    ready, notes = detect_checkout_entry_readiness(page)

    assert ready is False
    assert "cart_empty" in notes


def test_dismiss_common_interruptions_fails_safely() -> None:
    page = FakePage(fail_locator=True)
    notes = dismiss_common_interruptions(page)
    assert notes == []


def test_collect_semantic_page_signals_detects_nopcommerce_anchors() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/cart",
        selectors={
            "input[name*='captcha']": [{"visible": True}],
            "input[name*='otp']": [{"visible": True}],
            "input[name*='cvv']": [{"visible": True}],
            "div.product-essential": [{"visible": True}],
            ".shopping-cart-page": [{"visible": True}],
            "#checkout": [{"visible": True}],
        },
    )

    signals = collect_semantic_page_signals(page)

    assert "captcha_visible" in signals
    assert "otp_required" in signals
    assert "payment_auth_required" in signals
    assert "product_anchor_present" in signals
    assert "cart_anchor_present" in signals
    assert "checkout_anchor_present" in signals


def test_detect_access_denied_uses_title_and_body_markers() -> None:
    page = FakePage(
        url="https://demo.nopcommerce.com/",
        title="Access Denied",
        selectors={
            "body": [
                {
                    "text": (
                        "You don't have permission to access \"http://demo.nopcommerce.com/\" "
                        "on this server. Reference #18.6518d017 https://errors.edgesuite.net/"
                    ),
                    "visible": True,
                }
            ]
        },
    )

    assert detect_access_denied(page) is True
    assert classify_page_state(page) == "unknown"


def test_duplicate_search_guard_skips_immediate_repeat() -> None:
    action_guard.clear()
    session_id = uuid4()
    first_url = "https://demo.nopcommerce.com/search?q=htc+phone"

    assert action_guard.should_skip_duplicate_search(
        session_id,
        query="htc phone",
        current_url=first_url,
    ) is False

    action_guard.record_search(session_id, query="htc phone", current_url=first_url)
    assert action_guard.should_skip_duplicate_search(
        session_id,
        query="htc phone",
        current_url=first_url,
    ) is True
    assert action_guard.should_skip_duplicate_search(
        session_id,
        query="nokia phone",
        current_url=first_url,
    ) is False


def test_recovery_helper_returns_stable_shape() -> None:
    page = FakePage(url="https://demo.nopcommerce.com/somewhere")
    recovery = recover_to_stable_page(page, preferred="cart")
    assert set(recovery.keys()) == {"target", "success", "landed_url", "notes"}
    assert recovery["target"] == "cart"
    assert recovery["success"] is True
    assert isinstance(recovery["landed_url"], str)

    failing_page = FakePage(fail_goto=True)
    failure = recover_to_stable_page(failing_page, preferred="home")
    assert set(failure.keys()) == {"target", "success", "landed_url", "notes"}
    assert failure["success"] is False
