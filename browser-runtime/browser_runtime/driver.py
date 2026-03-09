from __future__ import annotations

import logging
import threading
from typing import Any, Dict
from uuid import UUID

try:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
except ImportError:  # Playwright not installed
    Browser = BrowserContext = Page = Playwright = object  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


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
        self._playwright_started = False
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: Dict[UUID, BrowserContext] = {}
        self._pages: Dict[UUID, Page | DummyPage] = {}

    def _ensure_browser_started(self) -> None:
        with self._lock:
            if self._playwright_started:
                return

            if sync_playwright is None:
                logger.warning("Playwright not available; running in no-op mode.")
                self._playwright_started = True
                self._browser = None
                return

            playwright: Playwright | None = None
            try:
                playwright = sync_playwright().start()
                browser = playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
            except Exception as exc:
                logger.warning(
                    "Playwright launch failed; running in no-op mode: %s",
                    exc,
                )
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

        context = self._browser.new_context()
        page = context.new_page()
        self._contexts[session_id] = context
        self._pages[session_id] = page
        return page

    def get_page(self, session_id: UUID) -> Page | DummyPage:
        with self._lock:
            self._ensure_browser_started()

            if session_id in self._pages:
                return self._pages[session_id]

            return self._create_page_for_session(session_id)

    def get_amazon_auth_status(self, session_id: UUID) -> dict[str, Any]:
        with self._lock:
            self._ensure_browser_started()
            page = self.get_page(session_id)
            context = self._contexts.get(session_id)
            current_url = getattr(page, "url", None)
            current_url_text = current_url if isinstance(current_url, str) and current_url else None
            if context is None:
                return {
                    "connected": False,
                    "cookie_count": 0,
                    "current_url": current_url_text,
                    "notes": "No Playwright browser context is available for this session.",
                }

            cookies_fn = getattr(context, "cookies", None)
            if not callable(cookies_fn):
                return {
                    "connected": False,
                    "cookie_count": 0,
                    "current_url": current_url_text,
                    "notes": "Browser context does not expose cookies.",
                }

            try:
                raw_cookies = cookies_fn()
            except Exception as exc:
                logger.debug("Failed to inspect browser cookies for session %s", session_id, exc_info=True)
                return {
                    "connected": False,
                    "cookie_count": 0,
                    "current_url": current_url_text,
                    "notes": f"Cookie inspection failed: {exc}",
                }

            amazon_cookies = [
                cookie
                for cookie in raw_cookies or []
                if isinstance(cookie, dict) and "amazon.in" in str(cookie.get("domain", "")).lower()
            ]
            return {
                "connected": len(amazon_cookies) > 0,
                "cookie_count": len(amazon_cookies),
                "current_url": current_url_text,
                "notes": None if amazon_cookies else "No amazon.in cookies detected in the runtime session.",
            }

    def close_session(self, session_id: UUID) -> None:
        with self._lock:
            context = self._contexts.pop(session_id, None)
            self._pages.pop(session_id, None)

            if context is not None:
                try:
                    context.close()
                except Exception:
                    logger.debug("Failed to close context for session %s", session_id, exc_info=True)

    def shutdown(self) -> None:
        with self._lock:
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


browser_session_manager = BrowserSessionManager()
