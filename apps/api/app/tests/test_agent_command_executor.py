from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from app.agent.state import AgentCommand, AgentCommandType
from app.schemas.session import Merchant
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.executor import AgentCommandExecutor


class FakeBrowserRuntimeClient(BrowserRuntimeClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def navigate_to_search_results(
        self,
        *,
        session_id: UUID,
        query: str | None,
        merchant: Merchant | None,
    ) -> None:
        self.calls.append(
            {
                "method": "navigate_to_search_results",
                "session_id": session_id,
                "query": query,
                "merchant": merchant,
            }
        )

    def inspect_product_page(
        self,
        *,
        session_id: UUID,
        page_type: str | None,
    ) -> None:
        self.calls.append(
            {
                "method": "inspect_product_page",
                "session_id": session_id,
                "page_type": page_type,
            }
        )

    def verify_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "verify_product_variant",
                "session_id": session_id,
                "variant_hint": variant_hint,
                "size_hint": size_hint,
                "color_hint": color_hint,
            }
        )

    def select_product_variant(
        self,
        *,
        session_id: UUID,
        variant_hint: str | None = None,
        size_hint: str | None = None,
        color_hint: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "select_product_variant",
                "session_id": session_id,
                "variant_hint": variant_hint,
                "size_hint": size_hint,
                "color_hint": color_hint,
            }
        )

    def add_to_cart(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self.calls.append(
            {
                "method": "add_to_cart",
                "session_id": session_id,
            }
        )

    def review_cart(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self.calls.append(
            {
                "method": "review_cart",
                "session_id": session_id,
            }
        )

    def perform_checkout(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self.calls.append(
            {
                "method": "perform_checkout",
                "session_id": session_id,
            }
        )

    def finalize_purchase(
        self,
        *,
        session_id: UUID,
    ) -> None:
        self.calls.append(
            {
                "method": "finalize_purchase",
                "session_id": session_id,
            }
        )

    def handle_error_recovery(
        self,
        *,
        session_id: UUID,
        error_type: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "method": "handle_error_recovery",
                "session_id": session_id,
                "error_type": error_type,
            }
        )

    def get_current_page_observation(self, *, session_id: UUID) -> dict[str, Any]:
        self.calls.append(
            {
                "method": "get_current_page_observation",
                "session_id": session_id,
            }
        )
        return {}

    def get_current_page_screenshot(self, *, session_id: UUID) -> dict[str, Any]:
        self.calls.append(
            {
                "method": "get_current_page_screenshot",
                "session_id": session_id,
            }
        )
        return {}


def test_execute_navigate_to_search_results_maps_payload() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(
        type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS,
        payload={"query": "dog food", "merchant": Merchant.AMAZON},
    )

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "navigate_to_search_results"
    assert fake.calls[0]["query"] == "dog food"
    assert fake.calls[0]["merchant"] == Merchant.AMAZON


def test_execute_inspect_product_page_mapping() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(
        type=AgentCommandType.INSPECT_PRODUCT_PAGE,
        payload={"page_type": "search_results"},
    )

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "inspect_product_page"
    assert fake.calls[0]["page_type"] == "search_results"


def test_execute_perform_checkout_mapping() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(
        type=AgentCommandType.PERFORM_CHECKOUT,
        payload={},
    )

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "perform_checkout"


def test_execute_error_recovery_mapping() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(
        type=AgentCommandType.HANDLE_ERROR_RECOVERY,
        payload={"error_type": "navigation_error"},
    )

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "handle_error_recovery"
    assert fake.calls[0]["error_type"] == "navigation_error"


@pytest.mark.skip(reason="Deferred full-checkout/order-placement command outside bounded Phase 2 nopCommerce flow.")
def test_execute_mark_order_placed_mapping() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(
        type=AgentCommandType.MARK_ORDER_PLACED,
        payload={},
    )

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "finalize_purchase"


def test_execute_select_variant_mapping() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(
        type=AgentCommandType.SELECT_PRODUCT_VARIANT,
        payload={"variant_hint": "3kg", "size_hint": "3kg"},
    )

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "select_product_variant"
    assert fake.calls[0]["variant_hint"] == "3kg"
    assert fake.calls[0]["size_hint"] == "3kg"


def test_execute_add_to_cart_mapping() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    command = AgentCommand(type=AgentCommandType.ADD_TO_CART, payload={})

    executor.execute(session_id, command)

    assert len(fake.calls) == 1
    assert fake.calls[0]["method"] == "add_to_cart"


def test_execute_many_preserves_order() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    commands = [
        AgentCommand(
            type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS,
            payload={"query": "dog food", "merchant": "demo.nopcommerce.com"},
        ),
        AgentCommand(type=AgentCommandType.REVIEW_CART, payload={}),
        AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT, payload={}),
    ]

    executor.execute_many(session_id, commands)

    assert len(fake.calls) == 3
    assert fake.calls[0]["method"] == "navigate_to_search_results"
    assert fake.calls[1]["method"] == "review_cart"
    assert fake.calls[2]["method"] == "perform_checkout"
