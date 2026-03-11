from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from app.schemas.session import Merchant
from app.tools.browser_runtime import BrowserRuntimeClient

logger = logging.getLogger(__name__)


class HttpBrowserRuntimeClient(BrowserRuntimeClient):
    def __init__(self, *, base_url: str, timeout_seconds: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._timeout = httpx.Timeout(connect=5.0, write=5.0, pool=5.0, read=30.0)
        self._observation_timeout = httpx.Timeout(
            connect=5.0,
            write=5.0,
            pool=5.0,
            read=60.0,
        )
        self._screenshot_timeout = httpx.Timeout(
            connect=5.0,
            write=5.0,
            pool=5.0,
            read=90.0,
        )

    def _post(self, path: str, payload: dict[str, Any]) -> None:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.post(path, json=payload)
        except Exception as exc:
            logger.warning(
                "browser_runtime_request_failed path=%s error=%s",
                path,
                exc,
            )
            return

        if 200 <= response.status_code < 300:
            return

        logger.warning(
            "browser_runtime_non_2xx path=%s status_code=%s body=%s",
            path,
            response.status_code,
            response.text[:300],
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.post(path, json=payload)
        except Exception as exc:
            logger.warning(
                "browser_runtime_request_failed path=%s error=%s",
                path,
                exc,
            )
            return {}

        if not (200 <= response.status_code < 300):
            logger.warning(
                "browser_runtime_non_2xx path=%s status_code=%s body=%s",
                path,
                response.status_code,
                response.text[:300],
            )
            return {}

        try:
            payload_json = response.json()
        except Exception as exc:
            logger.warning(
                "browser_runtime_invalid_json path=%s error=%s",
                path,
                exc,
            )
            return {}
        return payload_json if isinstance(payload_json, dict) else {}

    def _get_json(
        self,
        path: str,
        *,
        timeout: httpx.Timeout | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=timeout or self._timeout,
            ) as client:
                response = client.get(path, params=params)
        except Exception as exc:
            logger.warning(
                "browser_runtime_get_failed path=%s error=%s",
                path,
                exc,
            )
            return {}

        if not (200 <= response.status_code < 300):
            logger.warning(
                "browser_runtime_get_non_2xx path=%s status_code=%s body=%s",
                path,
                response.status_code,
                response.text[:300],
            )
            return {}

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "browser_runtime_get_invalid_json path=%s error=%s",
                path,
                exc,
            )
            return {}

        return payload if isinstance(payload, dict) else {}

    def navigate_to_search_results(
        self,
        *,
        session_id: UUID,
        query: str | None,
        merchant: Merchant | None,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/navigate_to_search_results",
            {
                "query": query,
                "merchant": merchant.value if merchant else None,
            },
        )

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
        candidate_url: str | None = None,
        candidate_title: str | None = None,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/inspect_product_page",
            {
                "page_type": page_type,
                "candidate_url": candidate_url,
                "candidate_title": candidate_title,
            },
        )

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/verify_product_variant",
            {
                "variant_hint": variant_hint,
                "size_hint": size_hint,
                "color_hint": color_hint,
            },
        )

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/select_variant",
            {
                "variant_hint": variant_hint,
                "size_hint": size_hint,
                "color_hint": color_hint,
            },
        )

    def add_to_cart(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/add_to_cart",
            {},
        )

    def review_cart(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/review_cart",
            {},
        )

    def remove_cart_item(
        self,
        *,
        session_id: UUID,
        item_id: str | None = None,
        title: str | None = None,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/remove_cart_item",
            {
                "item_id": item_id,
                "title": title,
            },
        )

    def update_cart_quantity(
        self,
        *,
        session_id: UUID,
        item_id: str | None = None,
        title: str | None = None,
        quantity: int,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/update_cart_quantity",
            {
                "item_id": item_id,
                "title": title,
                "quantity": quantity,
            },
        )

    def perform_checkout(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/perform_checkout",
            {},
        )

    def finalize_purchase(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/finalize_purchase",
            {},
        )

    def navigate_orders_history(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/navigate_orders_history",
            {},
        )

    def cancel_latest_order(
        self,
        *,
        session_id: UUID,
    ) -> dict[str, Any]:
        return self._post_json(
            f"/sessions/{session_id}/actions/cancel_latest_order",
            {},
        )

    def handle_error_recovery(
        self,
        *,
        session_id: UUID,
        error_type: str | None = None,
    ) -> None:
        self._post(
            f"/sessions/{session_id}/actions/handle_error_recovery",
            {
                "error_type": error_type,
            },
        )

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        return self._get_json(
            f"/sessions/{session_id}/observation/current_page",
            timeout=self._observation_timeout,
        )

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        return self._get_json(
            f"/sessions/{session_id}/observation/screenshot",
            timeout=self._screenshot_timeout,
        )

    def get_connection_status(
        self,
        *,
        session_id: UUID,
        merchant_domain: str,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.get(
                    f"/sessions/{session_id}/observation/auth_status",
                    params={"merchant_domain": merchant_domain},
                )
        except Exception as exc:
            raise RuntimeError(f"Failed to reach browser runtime: {exc}") from exc

        if not response.is_success:
            detail = response.text.strip() or "browser runtime rejected the status request"
            raise RuntimeError(detail)

        try:
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"browser runtime returned invalid status JSON: {exc}") from exc

        return payload if isinstance(payload, dict) else {}

    def set_connection_cookies(
        self,
        *,
        session_id: UUID,
        cookies: str,
        merchant_domain: str,
    ) -> None:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.post(
                    f"/sessions/{session_id}/cookies",
                    json={
                        "cookies": cookies,
                        "merchant_domain": merchant_domain,
                    },
                )
        except Exception as exc:
            raise RuntimeError(f"Failed to reach browser runtime: {exc}") from exc

        if response.is_success:
            return

        detail = response.text.strip() or "browser runtime rejected the cookie payload"
        raise RuntimeError(detail)

    def get_amazon_auth_status(self, *, session_id: UUID) -> dict[str, Any]:
        return self.get_connection_status(session_id=session_id, merchant_domain="amazon.in")

    def set_amazon_cookies(self, *, session_id: UUID, cookies: str) -> None:
        self.set_connection_cookies(
            session_id=session_id,
            cookies=cookies,
            merchant_domain="amazon.in",
        )
