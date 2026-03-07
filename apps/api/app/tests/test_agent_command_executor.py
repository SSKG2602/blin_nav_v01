from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

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
    ) -> None:
        self.calls.append(
            {
                "method": "verify_product_variant",
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


def test_execute_many_preserves_order() -> None:
    fake = FakeBrowserRuntimeClient()
    executor = AgentCommandExecutor(fake)
    session_id = uuid4()
    commands = [
        AgentCommand(
            type=AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS,
            payload={"query": "dog food", "merchant": "amazon.in"},
        ),
        AgentCommand(type=AgentCommandType.REVIEW_CART, payload={}),
        AgentCommand(type=AgentCommandType.PERFORM_CHECKOUT, payload={}),
    ]

    executor.execute_many(session_id, commands)

    assert len(fake.calls) == 3
    assert fake.calls[0]["method"] == "navigate_to_search_results"
    assert fake.calls[1]["method"] == "review_cart"
    assert fake.calls[2]["method"] == "perform_checkout"
