from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from browser_runtime.main import app


client = TestClient(app)


def test_navigate_to_search_results_action() -> None:
    session_id = uuid4()
    response = client.post(
        f"/sessions/{session_id}/actions/navigate_to_search_results",
        json={"query": "dog food", "merchant": "amazon.in"},
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


def test_review_cart_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/review_cart")
    assert response.status_code == 204


def test_perform_checkout_action_allows_empty_body() -> None:
    session_id = uuid4()
    response = client.post(f"/sessions/{session_id}/actions/perform_checkout")
    assert response.status_code == 204


def test_handle_error_recovery_action() -> None:
    session_id = uuid4()
    response = client.post(
        f"/sessions/{session_id}/actions/handle_error_recovery",
        json={"error_type": "navigation_error"},
    )
    assert response.status_code == 204


def test_health_live() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_health_ready() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

