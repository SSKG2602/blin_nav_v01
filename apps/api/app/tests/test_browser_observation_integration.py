from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.agent.observation import (
    build_page_understanding_from_browser_observation,
    capture_page_understanding_hybrid,
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


def test_http_browser_runtime_variant_and_add_to_cart_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, path: str, json: dict[str, Any]):
            captured.append((path, json))
            return _FakeResponse(status_code=204, payload={})

    monkeypatch.setattr("app.tools.http_browser_runtime.httpx.Client", _FakeClient)

    client = HttpBrowserRuntimeClient(base_url="http://runtime")
    session_id = uuid4()
    client.select_product_variant(
        session_id=session_id,
        variant_hint="3kg",
        size_hint="3kg",
    )
    client.add_to_cart(session_id=session_id)

    assert captured[0][0] == f"/sessions/{session_id}/actions/select_variant"
    assert captured[0][1]["variant_hint"] == "3kg"
    assert captured[1][0] == f"/sessions/{session_id}/actions/add_to_cart"


def test_http_browser_runtime_finalize_purchase_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, path: str, json: dict[str, Any]):
            captured.append((path, json))
            return _FakeResponse(status_code=204, payload={})

    monkeypatch.setattr("app.tools.http_browser_runtime.httpx.Client", _FakeClient)

    client = HttpBrowserRuntimeClient(base_url="http://runtime")
    session_id = uuid4()
    client.finalize_purchase(session_id=session_id)

    assert captured == [(f"/sessions/{session_id}/actions/finalize_purchase", {})]


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


def test_http_browser_runtime_screenshot_success(monkeypatch: pytest.MonkeyPatch) -> None:
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
                payload={"image_base64": "ZmFrZQ==", "mime_type": "image/png", "source": "runtime"},
            )

    monkeypatch.setattr("app.tools.http_browser_runtime.httpx.Client", _FakeClient)

    client = HttpBrowserRuntimeClient(base_url="http://runtime")
    session_id = uuid4()
    payload = client.get_current_page_screenshot(session_id=session_id)

    assert captured["path"] == f"/sessions/{session_id}/observation/screenshot"
    assert payload["mime_type"] == "image/png"


def test_http_browser_runtime_screenshot_failure_returns_empty_dict(
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
    payload = client.get_current_page_screenshot(session_id=uuid4())

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

        def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
            return {}

    understanding = capture_page_understanding(_FakeBrowserClient(), uuid4())

    assert understanding.page_type == PageType.CART
    assert understanding.cart_item_count == 2


def test_capture_page_understanding_hybrid_invokes_visual_fallback_on_weak_evidence() -> None:
    class _FakeBrowserClient:
        def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
            return {
                "observed_url": "https://example.invalid/unknown",
                "page_title": "Unknown page",
            }

        def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
            return {"image_base64": "ZmFrZQ==", "mime_type": "image/png"}

    class _FakeLLMClient:
        def __init__(self) -> None:
            self.called = False

        def analyze_visual_page(
            self,
            *,
            raw_observation: dict[str, object],
            screenshot: dict[str, object] | None,
        ) -> dict[str, object]:
            self.called = True
            return {
                "page_type": "PRODUCT_DETAIL",
                "primary_product": {"title": "Pedigree Dog Food", "price_text": "₹799"},
                "notes": "visual fallback applied",
            }

    llm = _FakeLLMClient()
    understanding, raw_observation, screenshot = capture_page_understanding_hybrid(
        _FakeBrowserClient(),
        llm,
        uuid4(),
    )

    assert llm.called is True
    assert understanding.page_type == PageType.PRODUCT_DETAIL
    assert understanding.primary_product is not None
    assert isinstance(raw_observation, dict)
    assert isinstance(screenshot, dict)


def test_capture_page_understanding_hybrid_uses_ocr_before_visual_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeBrowserClient:
        def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
            return {
                "observed_url": "https://www.amazon.in/gp/cart/view.html",
                "page_title": "Amazon",
            }

        def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
            return {"image_base64": "ZmFrZQ==", "mime_type": "image/png"}

    class _FakeLLMClient:
        def __init__(self) -> None:
            self.called = False

        def analyze_visual_page(
            self,
            *,
            raw_observation: dict[str, object],
            screenshot: dict[str, object] | None,
        ) -> dict[str, object]:
            self.called = True
            return {}

    monkeypatch.setattr(
        "app.agent.observation.extract_text_from_screenshot",
        lambda screenshot_payload: "Shopping Cart subtotal (2 items) Proceed to Buy ₹799",
    )

    llm = _FakeLLMClient()
    understanding, raw_observation, _ = capture_page_understanding_hybrid(
        _FakeBrowserClient(),
        llm,
        uuid4(),
    )

    assert llm.called is False
    assert understanding.page_type == PageType.CART
    assert isinstance(raw_observation, dict)
