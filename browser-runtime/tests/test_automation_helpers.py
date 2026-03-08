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
    choose_best_product_candidate,
    collect_semantic_page_signals,
    dismiss_common_interruptions,
    extract_cart_evidence,
    extract_product_detail_evidence,
    recover_to_stable_page,
    select_variant_option,
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

    def click(self, timeout: int | None = None) -> None:
        if self._entries:
            self._entries[0]["clicked"] = True

    def fill(self, value: str, timeout: int | None = None) -> None:
        if self._entries:
            self._entries[0]["filled"] = value

    def press(self, key: str) -> None:
        if self._entries:
            self._entries[0]["pressed"] = key

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
        url: str = "https://www.amazon.in",
        title: str = "Amazon",
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


def test_choose_best_product_candidate_prefers_non_junk_dp_link() -> None:
    candidates = [
        {
            "title": "Sponsored listing",
            "url": "https://www.amazon.in/slredirect/picassoRedirect.html",
            "price_text": "₹499",
        },
        {
            "title": "Pedigree Adult Dry Dog Food 3kg",
            "url": "https://www.amazon.in/dp/B012345678",
            "price_text": "₹899",
        },
    ]

    chosen = choose_best_product_candidate(candidates)

    assert chosen is not None
    assert chosen["url"] == "https://www.amazon.in/dp/B012345678"


def test_extract_product_detail_evidence_handles_complete_and_partial_fields() -> None:
    page = FakePage(
        url="https://www.amazon.in/dp/B012345678",
        title="Pedigree Product",
        selectors={
            "#productTitle": [{"text": "Pedigree Adult Dry Dog Food"}],
            "span.a-price span.a-offscreen": [{"text": "₹899.00"}],
            "#availability span": [{"text": "In stock"}],
            "#acrPopover span.a-icon-alt": [{"text": "4.3 out of 5 stars"}],
            "#acrCustomerReviewText": [{"text": "12,345 ratings"}],
            "#bylineInfo": [{"text": "Brand: Pedigree"}],
        },
    )

    evidence = extract_product_detail_evidence(page)
    assert evidence["title"] == "Pedigree Adult Dry Dog Food"
    assert evidence["price_text"] == "₹899.00"
    assert evidence["availability_text"] == "In stock"
    assert evidence["notes"] is None

    partial_page = FakePage(
        url="https://www.amazon.in/dp/B0PARTIAL",
        title="Unknown Product",
        selectors={"#productTitle": [{"text": "Unknown Product"}]},
    )
    partial_evidence = extract_product_detail_evidence(partial_page)
    assert partial_evidence["title"] == "Unknown Product"
    assert partial_evidence["price_text"] is None
    assert "price_missing" in (partial_evidence["notes"] or "")


def test_extract_cart_evidence_returns_count_and_checkout_ready() -> None:
    page = FakePage(
        url="https://www.amazon.in/gp/cart/view.html",
        selectors={
            "#sc-subtotal-label-buybox": [{"text": "Subtotal (2 items):"}],
            'input[name="proceedToRetailCheckout"]': [{"visible": True}],
        },
    )

    evidence = extract_cart_evidence(page)

    assert evidence["cart_item_count"] == 2
    assert evidence["checkout_ready"] is True


def test_dismiss_common_interruptions_fails_safely() -> None:
    page = FakePage(fail_locator=True)
    notes = dismiss_common_interruptions(page)
    assert notes == []


def test_collect_semantic_page_signals_detects_checkpoint_and_structure_anchors() -> None:
    page = FakePage(
        url="https://www.amazon.in/gp/buy/spc/handlers/display.html",
        selectors={
            "input#captchacharacters": [{"visible": True}],
            "input[name*='otp']": [{"visible": True}],
            "input[name*='cvv']": [{"visible": True}],
            "#productTitle": [{"visible": True}],
            "#sc-subtotal-label-buybox": [{"visible": True}],
            "#submitOrderButtonId": [{"visible": True}],
        },
    )

    signals = collect_semantic_page_signals(page)

    assert "captcha_visible" in signals
    assert "otp_required" in signals
    assert "payment_auth_required" in signals
    assert "product_anchor_present" in signals
    assert "cart_anchor_present" in signals
    assert "checkout_anchor_present" in signals


def test_duplicate_search_guard_skips_immediate_repeat() -> None:
    action_guard.clear()
    session_id = uuid4()
    first_url = "https://www.amazon.in/s?k=dog+food"

    assert action_guard.should_skip_duplicate_search(
        session_id,
        query="dog food",
        current_url=first_url,
    ) is False

    action_guard.record_search(session_id, query="dog food", current_url=first_url)
    assert action_guard.should_skip_duplicate_search(
        session_id,
        query="dog food",
        current_url=first_url,
    ) is True
    assert action_guard.should_skip_duplicate_search(
        session_id,
        query="cat food",
        current_url=first_url,
    ) is False


def test_recovery_helper_returns_stable_shape() -> None:
    page = FakePage(url="https://www.amazon.in/somewhere")
    recovery = recover_to_stable_page(page, preferred="cart")
    assert set(recovery.keys()) == {"target", "success", "landed_url", "notes"}
    assert recovery["target"] == "cart"
    assert recovery["success"] is True
    assert isinstance(recovery["landed_url"], str)

    failing_page = FakePage(fail_goto=True)
    failure = recover_to_stable_page(failing_page, preferred="home")
    assert set(failure.keys()) == {"target", "success", "landed_url", "notes"}
    assert failure["success"] is False


def test_select_variant_option_matches_hint_and_records_guard() -> None:
    action_guard.clear()
    session_id = uuid4()
    page = FakePage(
        url="https://www.amazon.in/dp/B012345678",
        selectors={
            "#twister .a-button-text": [
                {"text": "1kg", "visible": True},
                {"text": "3kg", "visible": True},
            ],
        },
    )

    selected, notes, signature = select_variant_option(
        page,
        session_id=session_id,
        variant_hint="3kg",
    )
    assert selected is True
    assert signature == "3kg"
    assert any("variant_selected" in note for note in notes)

    selected_again, notes_again, _ = select_variant_option(
        page,
        session_id=session_id,
        variant_hint="3kg",
    )
    assert selected_again is True
    assert "duplicate_variant_selection_skipped" in notes_again


def test_add_to_cart_duplicate_guard_skips_repeat() -> None:
    action_guard.clear()
    session_id = uuid4()
    page = FakePage(
        url="https://www.amazon.in/dp/B012345678",
        selectors={
            "#add-to-cart-button": [{"visible": True}],
        },
    )

    added, notes = add_current_product_to_cart(page, session_id=session_id)
    assert added is True
    assert any("add_to_cart_clicked" in note for note in notes)

    added_again, notes_again = add_current_product_to_cart(page, session_id=session_id)
    assert added_again is True
    assert "duplicate_add_to_cart_skipped" in notes_again


def test_duplicate_checkout_guard_skips_repeat_attempts() -> None:
    action_guard.clear()
    session_id = uuid4()
    current_url = "https://www.amazon.in/gp/cart/view.html"

    assert (
        action_guard.should_skip_duplicate_checkout_attempt(
            session_id,
            current_url=current_url,
        )
        is False
    )
    action_guard.record_checkout_attempt(session_id, current_url=current_url)
    assert (
        action_guard.should_skip_duplicate_checkout_attempt(
            session_id,
            current_url=current_url,
        )
        is True
    )
