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
from browser_runtime.observation.extractor import extract_observation_from_snapshot


client = TestClient(app)


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
            "observed_url": "https://www.amazon.in/s?k=dog+food",
            "page_title": "Amazon.in : dog food",
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
            "observed_url": "https://www.amazon.in/dp/B0TESTSKU",
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
            "observed_url": "https://www.amazon.in/gp/cart/view.html",
            "page_title": "Amazon Cart",
            "cart_item_count": 2,
        }
    )

    assert "cart" in observation.detected_page_hints
    assert observation.cart_item_count == 2


def test_checkout_like_observation_snapshot() -> None:
    observation = extract_observation_from_snapshot(
        {
            "observed_url": "https://www.amazon.in/gp/buy/spc/handlers/display.html",
            "page_title": "Checkout - Address",
            "checkout_ready": True,
        }
    )

    assert "checkout" in observation.detected_page_hints
    assert observation.checkout_ready is True
