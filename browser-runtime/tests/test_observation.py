from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from browser_runtime.driver import browser_session_manager
from browser_runtime.main import app
from browser_runtime.observation.extractor import (
    extract_current_page_observation,
    extract_observation_from_snapshot,
)


client = TestClient(app)


class _BodyLocator:
    def __init__(
        self,
        text: str,
        *,
        visible: bool = True,
        count: int = 1,
        attrs: dict[str, Any] | None = None,
        nested: dict[str, list[dict[str, Any]] | dict[str, Any]] | None = None,
    ) -> None:
        self._text = text
        self._visible = visible
        self._count = count
        self._attrs = attrs or {}
        self._nested = nested or {}

    @property
    def first(self) -> _BodyLocator:
        return self

    def inner_text(self, timeout: int | None = None) -> str:
        return self._text

    def count(self) -> int:
        return self._count

    def is_visible(self, timeout: int | None = None) -> bool:
        return self._visible

    def get_attribute(self, attr_name: str, timeout: int | None = None) -> str | None:
        value = self._attrs.get(attr_name)
        return None if value is None else str(value)

    def locator(self, selector: str) -> _BodyLocator:
        entry = self._nested.get(selector)
        if isinstance(entry, list):
            return _BodyLocator("", visible=bool(entry), count=len(entry))
        if isinstance(entry, dict):
            return _BodyLocator(
                str(entry.get("text", "")),
                visible=bool(entry.get("visible", True)),
                attrs=entry.get("attrs"),
            )
        return _BodyLocator("", visible=False, count=0)


class _AccessDeniedPage:
    def __init__(self) -> None:
        self.url = "https://demo.nopcommerce.com/"

    def title(self) -> str:
        return "Access Denied"

    def locator(self, selector: str) -> _BodyLocator:
        if selector == "body":
            return _BodyLocator(
                "You don't have permission to access this server. "
                "Reference #18.6518d017 https://errors.edgesuite.net/"
            )
        return _BodyLocator("", visible=False, count=0)


def _force_dummy_mode() -> None:
    with browser_session_manager._lock:
        browser_session_manager._browser = None
        browser_session_manager._playwright = None
        browser_session_manager._playwright_started = True
        browser_session_manager._contexts.clear()
        browser_session_manager._pages.clear()


def test_dummy_mode_observation_endpoint_returns_unknown_safe_payload() -> None:
    _force_dummy_mode()
    session_id = uuid4()

    response = client.get(f"/sessions/{session_id}/observation/current_page")

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_page_hints"] == ["unknown"]
    assert payload["product_candidates"] == []
    assert payload["primary_product"] is None


def test_search_results_like_observation_snapshot() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://demo.nopcommerce.com/search?q=htc",
            "page_title": "Search",
            "product_candidates": [
                {
                    "title": "HTC One M8 Android L 5.0 Lollipop",
                    "price_text": "$245.00",
                    "url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
                },
                {
                    "title": "Nokia Lumia 1020",
                    "price_text": "$349.00",
                    "url": "https://demo.nopcommerce.com/nokia-lumia-1020",
                },
            ],
        }
    )

    assert "search_results" in observation.detected_page_hints
    assert len(observation.product_candidates) == 2


def test_product_detail_like_observation_snapshot() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://demo.nopcommerce.com/htc-one-m8-android-l-50-lollipop",
            "page_title": "HTC One M8 Android L 5.0 Lollipop",
            "primary_product": {
                "title": "HTC One M8 Android L 5.0 Lollipop",
                "price_text": "$245.00",
                "summary_text": "A lightweight Android handset with a bright screen.",
                "quantity_text": "Qty: 1",
                "availability_text": "Add to cart available",
            },
        }
    )

    assert "product_detail" in observation.detected_page_hints
    assert observation.primary_product is not None
    assert observation.primary_product["title"] == "HTC One M8 Android L 5.0 Lollipop"
    assert observation.primary_product["summary_text"] == "A lightweight Android handset with a bright screen."
    assert observation.primary_product["quantity_text"] == "Qty: 1"


def test_cart_like_observation_snapshot() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://demo.nopcommerce.com/cart",
            "page_title": "Shopping cart",
            "cart_item_count": 2,
        }
    )

    assert "cart" in observation.detected_page_hints
    assert observation.cart_item_count == 2


def test_checkout_like_observation_snapshot() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://demo.nopcommerce.com/login/checkoutasguest",
            "page_title": "Welcome, Please Sign In!",
            "checkout_ready": True,
        }
    )

    assert "checkout" in observation.detected_page_hints
    assert "guest_checkout_entry_visible" in observation.detected_page_hints
    assert observation.checkout_ready is True


def test_product_detail_current_page_observation_carries_blocker_hints() -> None:
    class _ConfigurablePage:
        url = "https://demo.nopcommerce.com/build-your-own-computer"

        def title(self) -> str:
            return "Build your own computer"

        def locator(self, selector: str) -> _BodyLocator:
            mapping = {
                "div.product-essential": _BodyLocator("", visible=True),
                "div.product-name h1": _BodyLocator("Build your own computer"),
                ".prices .actual-price": _BodyLocator("$1,200.00"),
                ".attributes label.text-prompt": _BodyLocator("Processor *"),
                "select[id^='product_attribute_']": _BodyLocator("", attrs={"value": "0"}),
                "body": _BodyLocator("Build your own computer Please select Processor"),
            }
            return mapping.get(selector, _BodyLocator("", visible=False, count=0))

    observation = extract_current_page_observation(_ConfigurablePage())

    assert "product_detail" in observation.detected_page_hints
    assert "option_selection_required" in observation.detected_page_hints


def test_access_denied_snapshot_is_not_classified_as_home() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://demo.nopcommerce.com/",
            "page_title": "Access Denied",
        }
    )

    assert observation.detected_page_hints[:2] == ["access_denied", "unknown"]
    assert observation.notes == "The demo store blocked the runtime browser session."


def test_access_denied_current_page_observation_returns_blocked_hints() -> None:
    observation = extract_current_page_observation(_AccessDeniedPage())

    assert observation.detected_page_hints == ["access_denied", "unknown"]
    assert observation.notes == "The demo store blocked the runtime browser session."


def test_dummy_mode_screenshot_endpoint_returns_safe_payload() -> None:
    _force_dummy_mode()
    session_id = uuid4()

    response = client.get(f"/sessions/{session_id}/observation/screenshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mime_type"] == "image/png"
    assert payload["source"] == "runtime"
    assert "image_base64" in payload
