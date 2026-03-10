from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import threading
from typing import Any, Dict
from uuid import UUID

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


def _normalize_same_site(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    if normalized in {"lax"}:
        return "Lax"
    if normalized in {"strict"}:
        return "Strict"
    if normalized in {"none", "no_restriction", "no restriction"}:
        return "None"
    return None


def _normalize_cookie_payload(cookie: Any) -> dict[str, Any]:
    if not isinstance(cookie, dict):
        raise ValueError("Each cookie entry must be an object.")

    name = cookie.get("name")
    value = cookie.get("value")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Each cookie must include a non-empty name.")
    if not isinstance(value, str):
        raise ValueError(f'Cookie "{name}" must include a string value.')

    normalized: dict[str, Any] = {
        "name": name,
        "value": value,
    }

    url = cookie.get("url")
    domain = cookie.get("domain")
    path = cookie.get("path")
    if isinstance(url, str) and url.strip():
        normalized["url"] = url.strip()
    elif isinstance(domain, str) and domain.strip():
        normalized["domain"] = domain.strip()
        normalized["path"] = path.strip() if isinstance(path, str) and path.strip() else "/"
    else:
        raise ValueError(f'Cookie "{name}" must include a valid url or domain.')

    expires = cookie.get("expires", cookie.get("expirationDate"))
    if isinstance(expires, (int, float)) and expires > 0:
        normalized["expires"] = float(expires)

    if isinstance(cookie.get("secure"), bool):
        normalized["secure"] = cookie["secure"]
    if isinstance(cookie.get("httpOnly"), bool):
        normalized["httpOnly"] = cookie["httpOnly"]

    same_site = _normalize_same_site(cookie.get("sameSite"))
    if same_site is not None:
        normalized["sameSite"] = same_site

    return normalized


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
            context = self._browser.new_context()
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

    def get_page(self, session_id: UUID) -> Page | DummyPage:
        def _run() -> Page | DummyPage:
            self._ensure_browser_started()

            if session_id in self._pages:
                return self._pages[session_id]

            return self._create_page_for_session(session_id)

        return self._executor.submit(_run).result()

    def navigate_to(self, session_id: UUID, url: str) -> None:
        def _run() -> None:
            self._ensure_browser_started()
            if session_id in self._pages:
                page = self._pages[session_id]
            else:
                page = self._create_page_for_session(session_id)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

        self._executor.submit(_run).result()

    def get_current_url(self, session_id: UUID) -> str | None:
        self.wait_for_navigation_complete(session_id)
        with self._lock:
            if self._navigating.get(session_id):
                return "navigating"

        def _run() -> str | None:
            self._ensure_browser_started()
            if session_id in self._pages:
                page = self._pages[session_id]
            else:
                page = self._create_page_for_session(session_id)
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
            if session_id in self._pages:
                page = self._pages[session_id]
            else:
                page = self._create_page_for_session(session_id)
            return extract_current_page_observation(page).model_dump()

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
            if session_id in self._pages:
                page = self._pages[session_id]
            else:
                page = self._create_page_for_session(session_id)
            return extract_current_page_screenshot(page).model_dump()

        return self._executor.submit(_run).result()

    def get_amazon_auth_status(self, session_id: UUID) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            self._ensure_browser_started()
            if session_id in self._pages:
                page = self._pages[session_id]
            else:
                page = self._create_page_for_session(session_id)
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

        return self._executor.submit(_run).result()

    def set_session_cookies(self, session_id: UUID, cookies_list: list[Any]) -> None:
        normalized_cookies = [_normalize_cookie_payload(cookie) for cookie in cookies_list]
        if not normalized_cookies:
            raise ValueError("No cookies were provided.")

        with self._lock:
            self._navigating[session_id] = True

        def _run() -> None:
            self._ensure_browser_started()
            if session_id not in self._pages:
                self._create_page_for_session(session_id)
            page = self._pages[session_id]
            context = self._contexts.get(session_id)
            if context is None:
                raise RuntimeError("No Playwright browser context is available for this session.")

            add_cookies_fn = getattr(context, "add_cookies", None)
            if not callable(add_cookies_fn):
                raise RuntimeError("Browser context does not support cookie injection.")

            try:
                page.goto("https://www.amazon.in", wait_until="domcontentloaded", timeout=30000)
                add_cookies_fn(normalized_cookies)
                page.reload(wait_until="domcontentloaded")
            except Exception:
                logger.exception("Asynchronous Amazon cookie navigation failed for session %s", session_id)
                raise
            finally:
                with self._lock:
                    self._navigating[session_id] = False

        try:
            self._executor.submit(_run)
        except Exception:
            with self._lock:
                self._navigating[session_id] = False
            raise

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
