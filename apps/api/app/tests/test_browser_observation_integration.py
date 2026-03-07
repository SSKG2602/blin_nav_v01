from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.agent.observation import (
    build_page_understanding_from_browser_observation,
    capture_page_understanding,
)
from app.schemas.page_understanding import PageType
from app.tools.http_browser_runtime import HttpBrowserRuntimeClient


class _FakeResponse:
    def __init__(self, *, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


def test_http_browser_runtime_observation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, path: str):
            captured["path"] = path
            return _FakeResponse(
                status_code=200,
                payload={
                    "observed_url": "https://www.amazon.in/s?k=dog+food",
                    "page_title": "Results",
                    "detected_page_hints": ["search_results"],
                    "product_candidates": [],
                    "primary_product": None,
                    "cart_item_count": None,
                    "checkout_ready": None,
                    "notes": None,
                },
            )

    monkeypatch.setattr("app.tools.http_browser_runtime.httpx.Client", _FakeClient)

    client = HttpBrowserRuntimeClient(base_url="http://runtime")
    session_id = uuid4()
    payload = client.get_current_page_observation(session_id=session_id)

    assert captured["path"] == f"/sessions/{session_id}/observation/current_page"
    assert payload["detected_page_hints"] == ["search_results"]


def test_http_browser_runtime_observation_failure_returns_empty_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, path: str):
            raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.tools.http_browser_runtime.httpx.Client", _FailingClient)

    client = HttpBrowserRuntimeClient(base_url="http://runtime")
    payload = client.get_current_page_observation(session_id=uuid4())

    assert payload == {}


def test_build_page_understanding_from_browser_observation() -> None:
    understanding = build_page_understanding_from_browser_observation(
        {
            "observed_url": "https://www.amazon.in/s?k=dog+food",
            "page_title": "Search results",
            "detected_page_hints": ["search_results"],
            "product_candidates": [
                {"title": "Pedigree Adult Dog Food", "price_text": "₹799"},
            ],
        }
    )

    assert understanding.page_type == PageType.SEARCH_RESULTS
    assert len(understanding.product_candidates) == 1
    assert understanding.primary_product is not None


def test_capture_page_understanding_from_browser_client() -> None:
    class _FakeBrowserClient:
        def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
            return {
                "observed_url": "https://www.amazon.in/gp/cart/view.html",
                "page_title": "Amazon Cart",
                "detected_page_hints": ["cart"],
                "cart_item_count": 2,
            }

    understanding = capture_page_understanding(_FakeBrowserClient(), uuid4())

    assert understanding.page_type == PageType.CART
    assert understanding.cart_item_count == 2

