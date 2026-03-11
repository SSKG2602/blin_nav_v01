from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from browser_runtime.driver import browser_session_manager
from browser_runtime.main import app


client = TestClient(app)


def force_dummy_mode() -> None:
    with browser_session_manager._lock:
        browser_session_manager._browser = None
        browser_session_manager._playwright = None
        browser_session_manager._playwright_started = True
        browser_session_manager._contexts.clear()
        browser_session_manager._pages.clear()


def test_navigate_to_search_results_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(
        f"/sessions/{session_id}/actions/navigate_to_search_results",
        json={"query": "dog food", "merchant": "demo.nopcommerce.com"},
    )
    assert resp.status_code == 204


def test_inspect_product_page_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(
        f"/sessions/{session_id}/actions/inspect_product_page",
        json={"page_type": "search_results"},
    )
    assert resp.status_code == 204


def test_verify_product_variant_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(f"/sessions/{session_id}/actions/verify_product_variant")
    assert resp.status_code == 204


def test_select_variant_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(
        f"/sessions/{session_id}/actions/select_variant",
        json={"variant_hint": "3kg"},
    )
    assert resp.status_code == 204


def test_add_to_cart_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(f"/sessions/{session_id}/actions/add_to_cart")
    assert resp.status_code == 204


def test_review_cart_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(f"/sessions/{session_id}/actions/review_cart")
    assert resp.status_code == 204


def test_perform_checkout_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(f"/sessions/{session_id}/actions/perform_checkout")
    assert resp.status_code == 204


@pytest.mark.skip(reason="Deferred full-checkout action outside bounded Phase 2 nopCommerce flow.")
def test_finalize_purchase_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(f"/sessions/{session_id}/actions/finalize_purchase")
    assert resp.status_code == 204


def test_handle_error_recovery_dummy_mode() -> None:
    force_dummy_mode()
    session_id = uuid4()
    resp = client.post(
        f"/sessions/{session_id}/actions/handle_error_recovery",
        json={"error_type": "navigation_error"},
    )
    assert resp.status_code == 204
