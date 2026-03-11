from __future__ import annotations

import sys
from pathlib import Path
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
    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def first(self) -> _BodyLocator:
        return self

    def inner_text(self, timeout: int | None = None) -> str:
        return self._text

    def count(self) -> int:
        return 1

    def is_visible(self, timeout: int | None = None) -> bool:
        return True


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
        return _BodyLocator("")


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
            "observed_url": "https://demo.nopcommerce.com/search?q=dog+food",
            "page_title": "Search",
            "product_candidates": [
                {"title": "Pedigree Adult Dog Food 3kg", "price_text": "₹799"},
                {"title": "Drools Dog Food 3kg", "price_text": "₹699"},
            ],
        }
    )

    assert "search_results" in observation.detected_page_hints
    assert len(observation.product_candidates) == 2


def test_product_detail_like_observation_snapshot() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://demo.nopcommerce.com/build-your-own-computer",
            "page_title": "Pedigree Adult Dog Food",
            "primary_product": {
                "title": "Pedigree Adult Dog Food",
                "price_text": "₹799",
                "availability_text": "In stock",
            },
        }
    )

    assert "product_detail" in observation.detected_page_hints
    assert observation.primary_product is not None
    assert observation.primary_product["title"] == "Pedigree Adult Dog Food"


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
            "observed_url": "https://demo.nopcommerce.com/checkout",
            "page_title": "Checkout - Address",
            "checkout_ready": True,
        }
    )

    assert "checkout" in observation.detected_page_hints
    assert observation.checkout_ready is True


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
