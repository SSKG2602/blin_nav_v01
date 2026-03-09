from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.schemas.session import Merchant


class BrowserRuntimeClient(Protocol):
    def navigate_to_search_results(
        self,
        *,
        session_id: UUID,
        query: str | None,
        merchant: Merchant | None,
    ) -> None:
        ...

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
        candidate_url: str | None = None,
        candidate_title: str | None = None,
    ) -> None:
        ...

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        ...

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        ...

    def add_to_cart(
        self,
        *,
        session_id: UUID,
    ) -> None:
        ...

    def review_cart(
        self,
        *,
        session_id: UUID,
    ) -> None:
        ...

    def remove_cart_item(
        self,
        *,
        session_id: UUID,
        item_id: str | None = None,
        title: str | None = None,
    ) -> None:
        ...

    def update_cart_quantity(
        self,
        *,
        session_id: UUID,
        item_id: str | None = None,
        title: str | None = None,
        quantity: int,
    ) -> None:
        ...

    def perform_checkout(
        self,
        *,
        session_id: UUID,
    ) -> None:
        ...

    def finalize_purchase(
        self,
        *,
        session_id: UUID,
    ) -> None:
        ...

    def navigate_orders_history(
        self,
        *,
        session_id: UUID,
    ) -> None:
        ...

    def cancel_latest_order(
        self,
        *,
        session_id: UUID,
    ) -> dict[str, Any]:
        ...

    def handle_error_recovery(
        self,
        *,
        session_id: UUID,
        error_type: str | None = None,
    ) -> None:
        ...

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        ...

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        ...

    def get_amazon_auth_status(self, *, session_id: UUID) -> dict[str, Any]:
        ...

    def set_amazon_cookies(self, *, session_id: UUID, cookies: str) -> None:
        ...
