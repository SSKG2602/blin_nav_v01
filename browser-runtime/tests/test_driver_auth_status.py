from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from browser_runtime.driver import BrowserSessionManager


class FakeContext:
    def __init__(self, cookies_payload: list[dict[str, object]] | None = None) -> None:
        self._cookies_payload = cookies_payload or []
        self.added_cookies: list[dict[str, object]] = []

    def cookies(self) -> list[dict[str, object]]:
        return list(self._cookies_payload)

    def add_cookies(self, cookies_payload: list[dict[str, object]]) -> None:
        self.added_cookies = list(cookies_payload)


class FakePage:
    def __init__(self, url: str = "https://www.bigbasket.com/") -> None:
        self.url = url
        self.goto_calls: list[str] = []
        self.reload_calls = 0

    def goto(self, url: str, **_: object) -> None:
        self.goto_calls.append(url)
        self.url = url

    def reload(self, **_: object) -> None:
        self.reload_calls += 1


@pytest.fixture
def manager() -> BrowserSessionManager:
    runtime_manager = BrowserSessionManager()
    runtime_manager._ensure_browser_started = lambda: None  # type: ignore[method-assign]
    try:
        yield runtime_manager
    finally:
        runtime_manager._executor.shutdown(wait=True)


def test_get_connection_status_matches_bigbasket_cookie_domains_safely(
    manager: BrowserSessionManager,
) -> None:
    session_id = uuid4()
    manager._pages[session_id] = FakePage()
    manager._contexts[session_id] = FakeContext(
        [
            {"domain": "bigbasket.com"},
            {"domain": ".bigbasket.com"},
            {"domain": "www.bigbasket.com"},
            {"domain": "images.bigbasket.com"},
            {"url": "https://checkout.bigbasket.com/cart"},
            {"domain": "notbigbasket.com"},
            {"domain": "totally-bigbasket.com.evil.test"},
            {"domain": "amazon.in"},
        ]
    )

    payload = manager.get_connection_status(session_id, merchant_domain="bigbasket.com")

    assert payload["connected"] is True
    assert payload["cookie_count"] == 5
    assert payload["current_url"] == "https://www.bigbasket.com/"
    assert payload["notes"] is None


def test_set_session_cookies_navigates_to_bigbasket_home(
    manager: BrowserSessionManager,
) -> None:
    session_id = uuid4()
    page = FakePage(url="about:blank")
    context = FakeContext()
    manager._pages[session_id] = page
    manager._contexts[session_id] = context

    manager.set_session_cookies(
        session_id,
        [{"domain": ".bigbasket.com", "name": "bb", "value": "cookie-value"}],
        merchant_domain="bigbasket.com",
    )
    manager.wait_for_navigation_complete(session_id, timeout_seconds=1)

    assert context.added_cookies == [
        {
            "domain": ".bigbasket.com",
            "name": "bb",
            "path": "/",
            "value": "cookie-value",
        }
    ]
    assert page.goto_calls == ["https://www.bigbasket.com"]
    assert page.reload_calls == 0
