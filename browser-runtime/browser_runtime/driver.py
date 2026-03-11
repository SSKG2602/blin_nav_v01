from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import logging
import threading
from typing import Any, Dict, TypeVar
from uuid import UUID

from browser_runtime.automation.helpers import (
    classify_page_state,
    detect_access_denied,
    detect_location_blocked,
)
from browser_runtime.observation.extractor import (
    extract_current_page_observation,
    extract_current_page_screenshot,
)

try:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
except ImportError:  # Playwright not installed
    Browser = BrowserContext = Page = Playwright = object  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
_PageResult = TypeVar("_PageResult")
_DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
_DEFAULT_BROWSER_CONTEXT_OPTIONS = {
    "user_agent": _DEFAULT_BROWSER_USER_AGENT,
    "locale": "en-IN",
    "timezone_id": "Asia/Kolkata",
    "viewport": {"width": 1440, "height": 900},
    "extra_http_headers": {"Accept-Language": "en-IN,en;q=0.9"},
}
_BROWSER_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'language', { get: () => 'en-IN' });
Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en'] });
Object.defineProperty(navigator, 'platform', { get: () => 'Linux x86_64' });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
"""


def _navigating_observation_payload() -> dict[str, Any]:
    return {
        "observed_url": "navigating",
        "page_title": None,
        "detected_page_hints": ["navigating"],
        "product_candidates": [],
        "primary_product": None,
        "cart_items": [],
        "cart_item_count": None,
        "checkout_ready": None,
        "order_id_hint": None,
        "order_date_text": None,
        "shipping_stage_text": None,
        "expected_delivery_text": None,
        "order_total_text": None,
        "order_card_title": None,
        "orders_page_url": None,
        "support_entry_hint": None,
        "returns_entry_hint": None,
        "notes": "Navigation in progress.",
    }


def _navigating_screenshot_payload() -> dict[str, Any]:
    return {
        "image_base64": None,
        "mime_type": "image/png",
        "source": "runtime",
        "notes": "Navigation in progress.",
    }


class DummyPage:
    def __init__(self, session_id: UUID):
        self._session_id = session_id
        self.url = ""

    def title(self) -> str:
        return "Dummy Browser Runtime Page"

    def goto(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.goto session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        if args and isinstance(args[0], str):
            self.url = args[0]
        return self

    def fill(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.fill session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return self

    def click(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.click session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return self

    def press(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.press session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return self

    def locator(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.locator session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return self

    def wait_for_selector(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.wait_for_selector session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return self

    def wait_for_load_state(self, *args, **kwargs) -> DummyPage:
        logger.info(
            "dummy_page.wait_for_load_state session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return self

    def inner_text(self, *args, **kwargs) -> str:
        logger.info(
            "dummy_page.inner_text session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return ""

    def count(self, *args, **kwargs) -> int:
        logger.info(
            "dummy_page.count session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return 0

    def is_visible(self, *args, **kwargs) -> bool:
        logger.info(
            "dummy_page.is_visible session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return False

    def screenshot(self, *args, **kwargs) -> bytes:
        logger.info(
            "dummy_page.screenshot session_id=%s args=%s kwargs=%s",
            self._session_id,
            args,
            kwargs,
        )
        return b""


class BrowserSessionManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._playwright_started = False
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: Dict[UUID, BrowserContext] = {}
        self._pages: Dict[UUID, Page | DummyPage] = {}
        self._navigating: Dict[UUID, bool] = {}

    def _is_browser_healthy(self) -> bool:
        try:
            if self._browser is None:
                return False
            _ = self._browser.contexts
            return True
        except Exception:
            return False

    def _ensure_browser_started(self) -> None:
        with self._lock:
            if self._playwright_started:
                if self._is_browser_healthy():
                    return
                logger.warning("Browser crashed, restarting...")
                self._playwright_started = False
                self._browser = None
                self._pages.clear()
                self._contexts.clear()
                self._navigating.clear()

            if sync_playwright is None:
                logger.warning("Playwright not available; running in no-op mode.")
                self._playwright_started = True
                self._browser = None
                return

            playwright: Playwright | None = None
            try:
                playwright = sync_playwright().start()
                logger.info("Launching Chromium browser...")
                browser = playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-zygote",
                        "--disable-blink-features=AutomationControlled",
                        "--lang=en-IN",
                    ],
                )
                logger.info("Chromium launched successfully.")
            except Exception as exc:
                logger.error("Chromium launch failed: %s", exc, exc_info=True)
                if playwright is not None:
                    try:
                        playwright.stop()
                    except Exception:
                        logger.debug("Playwright stop failed during fallback.", exc_info=True)
                self._playwright_started = True
                self._playwright = None
                self._browser = None
                return

            self._playwright = playwright
            self._browser = browser
            self._playwright_started = True

    def _create_page_for_session(self, session_id: UUID) -> Page | DummyPage:
        if self._browser is None:
            page = DummyPage(session_id)
            self._pages[session_id] = page
            return page

        try:
            context = self._browser.new_context(**_DEFAULT_BROWSER_CONTEXT_OPTIONS)
            add_init_script = getattr(context, "add_init_script", None)
            if callable(add_init_script):
                add_init_script(_BROWSER_INIT_SCRIPT)
            page = context.new_page()
            self._contexts[session_id] = context
            self._pages[session_id] = page
            return page
        except Exception as exc:
            logger.error("Failed to create page, browser may have crashed: %s", exc)
            self._playwright_started = False
            self._browser = None
            self._contexts.pop(session_id, None)
            self._pages.pop(session_id, None)
            page = DummyPage(session_id)
            self._pages[session_id] = page
            return page

    def _get_or_create_page_for_session(self, session_id: UUID) -> Page | DummyPage:
        page = self._pages.get(session_id)
        if page is not None:
            return page
        return self._create_page_for_session(session_id)

    def run_with_session_page(
        self,
        session_id: UUID,
        fn: Callable[[Page | DummyPage], _PageResult],
    ) -> _PageResult:
        def _run() -> _PageResult:
            self._ensure_browser_started()
            page = self._get_or_create_page_for_session(session_id)
            return fn(page)

        return self._executor.submit(_run).result()

    def get_page(self, session_id: UUID) -> Page | DummyPage:
        def _run() -> Page | DummyPage:
            self._ensure_browser_started()
            return self._get_or_create_page_for_session(session_id)

        return self._executor.submit(_run).result()

    def navigate_to(self, session_id: UUID, url: str) -> None:
        def _run() -> None:
            self._ensure_browser_started()
            page = self._get_or_create_page_for_session(session_id)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

        self._executor.submit(_run).result()

    def get_current_url(self, session_id: UUID) -> str | None:
        self.wait_for_navigation_complete(session_id)
        with self._lock:
            if self._navigating.get(session_id):
                return "navigating"

        def _run() -> str | None:
            self._ensure_browser_started()
            page = self._get_or_create_page_for_session(session_id)
            current_url = getattr(page, "url", None)
            return current_url if isinstance(current_url, str) and current_url else None

        return self._executor.submit(_run).result()

    def get_current_page_observation(self, session_id: UUID) -> dict[str, Any]:
        self.wait_for_navigation_complete(session_id)
        with self._lock:
            if self._navigating.get(session_id):
                return _navigating_observation_payload()

        def _run() -> dict[str, Any]:
            self._ensure_browser_started()
            page = self._get_or_create_page_for_session(session_id)
            payload = extract_current_page_observation(page).model_dump()
            blocked_hints: list[str] = []
            blocked_notes: list[str] = []
            if detect_location_blocked(page):
                blocked_hints.append("location_blocked")
                blocked_notes.append("Waiting for location selection.")
            if detect_access_denied(page):
                blocked_hints.extend(["access_denied", "unknown"])
                blocked_notes.append("The demo store blocked the runtime browser session.")
            page_state = classify_page_state(page)
            if page_state == "login":
                blocked_hints.append("login")
                blocked_notes.append("Sign-in required.")
            if blocked_hints:
                existing_hints = list(payload.get("detected_page_hints") or [])
                payload["detected_page_hints"] = list(dict.fromkeys([*blocked_hints, *existing_hints]))
                existing_notes = str(payload.get("notes") or "").strip()
                deduped_notes = list(
                    dict.fromkeys(part for part in [*blocked_notes, existing_notes or None] if part)
                )
                payload["notes"] = " ".join(deduped_notes)
            return payload

        return self._executor.submit(_run).result()

    def wait_for_navigation_complete(self, session_id: UUID, timeout_seconds: int = 15) -> None:
        import time

        start = time.time()
        while self._navigating.get(session_id, False):
            if time.time() - start > timeout_seconds:
                break
            time.sleep(0.3)

    def get_page_screenshot(self, session_id: UUID) -> dict[str, Any]:
        with self._lock:
            if self._navigating.get(session_id):
                return _navigating_screenshot_payload()

        def _run() -> dict[str, Any]:
            self._ensure_browser_started()
            page = self._get_or_create_page_for_session(session_id)
            return extract_current_page_screenshot(page).model_dump()

        return self._executor.submit(_run).result()

    def close_session(self, session_id: UUID) -> None:
        def _run() -> None:
            context = self._contexts.pop(session_id, None)
            self._pages.pop(session_id, None)

            if context is not None:
                try:
                    context.close()
                except Exception:
                    logger.debug("Failed to close context for session %s", session_id, exc_info=True)

        self._executor.submit(_run).result()

    def shutdown(self) -> None:
        def _run() -> None:
            for context in self._contexts.values():
                try:
                    context.close()
                except Exception:
                    logger.debug("Failed to close context during shutdown.", exc_info=True)
            self._contexts.clear()
            self._pages.clear()

            if self._browser is not None:
                try:
                    self._browser.close()
                except Exception:
                    logger.debug("Failed to close browser during shutdown.", exc_info=True)
                self._browser = None

            if self._playwright is not None:
                try:
                    self._playwright.stop()
                except Exception:
                    logger.debug("Failed to stop Playwright during shutdown.", exc_info=True)
                self._playwright = None

            self._playwright_started = False

        try:
            self._executor.submit(_run).result()
        finally:
            self._executor.shutdown(wait=True)


browser_session_manager = BrowserSessionManager()
