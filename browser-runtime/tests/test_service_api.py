from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from browser_runtime.main import app


client = TestClient(app)


def test_navigate_to_search_results_action() -> None:
    session_id = uuid4()
    response = client.post(
        f"/sessions/{session_id}/actions/navigate_to_search_results",
        json={"query": "dog food", "merchant": "demo.nopcommerce.com"},
    )
    assert response.status_code == 204


def test_inspect_product_page_action() -> None:
    session_id = uuid4()
    response = client.post(
        f"/sessions/{session_id}/actions/inspect_product_page",
        json={"page_type": "search_results"},
    )
    assert response.status_code == 204


def test_verify_product_variant_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/verify_product_variant")
    assert response.status_code == 204


def test_select_variant_action() -> None:
    session_id = uuid4()
    response = client.post(
        f"/sessions/{session_id}/actions/select_variant",
        json={"variant_hint": "3kg", "size_hint": "3kg"},
    )
    assert response.status_code == 204


def test_add_to_cart_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/add_to_cart")
    assert response.status_code == 204


def test_review_cart_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/review_cart")
    assert response.status_code == 204


def test_perform_checkout_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/perform_checkout")
    assert response.status_code == 204


@pytest.mark.skip(reason="Deferred full-checkout action outside bounded Phase 2 nopCommerce flow.")
def test_finalize_purchase_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/finalize_purchase")
    assert response.status_code == 204


def test_handle_error_recovery_action() -> None:
    session_id = uuid4()
    response = client.post(
        f"/sessions/{session_id}/actions/handle_error_recovery",
        json={"error_type": "navigation_error"},
    )
    assert response.status_code == 204


def test_cancel_latest_order_action_returns_structured_payload() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/cancel_latest_order")
    assert response.status_code == 200
    payload = response.json()
    assert "cancelled" in payload
    assert "spoken_summary" in payload


def test_health_live() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_health_ready() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_current_page_screenshot_observation_endpoint() -> None:
    session_id = uuid4()
    response = client.get(f"/sessions/{session_id}/observation/screenshot")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mime_type"] == "image/png"


def test_current_page_observation_endpoint_preserves_access_denied_hint(
    monkeypatch,
) -> None:
    session_id = uuid4()
    monkeypatch.setattr(
        "browser_runtime.routes.observation.browser_session_manager.get_current_url",
        lambda _: "https://demo.nopcommerce.com/",
    )
    monkeypatch.setattr(
        "browser_runtime.routes.observation.browser_session_manager.get_current_page_observation",
        lambda _: {
            "observed_url": "https://demo.nopcommerce.com/",
            "page_title": "Access Denied",
            "detected_page_hints": ["access_denied", "unknown"],
            "product_candidates": [],
            "primary_product": None,
            "cart_items": [],
            "cart_item_count": None,
            "checkout_ready": None,
            "notes": "The demo store blocked the runtime browser session.",
        },
    )

    response = client.get(f"/sessions/{session_id}/observation/current_page")

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_page_hints"] == ["access_denied", "unknown"]
    assert payload["notes"] == "The demo store blocked the runtime browser session."
