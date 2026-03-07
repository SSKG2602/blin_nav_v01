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
    ) -> None:
        ...

    def verify_product_variant(
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

    def perform_checkout(
        self,
        *,
        session_id: UUID,
    ) -> None:
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
