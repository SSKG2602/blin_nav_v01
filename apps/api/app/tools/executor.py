from __future__ import annotations

from uuid import UUID

from app.agent.state import AgentCommand, AgentCommandType
from app.schemas.session import Merchant
from app.tools.browser_runtime import BrowserRuntimeClient


class AgentCommandExecutor:
    def __init__(self, browser_client: BrowserRuntimeClient):
        self._browser = browser_client

    def execute(self, session_id: UUID, command: AgentCommand) -> None:
        payload = command.payload or {}

        if command.type == AgentCommandType.NAVIGATE_TO_SEARCH_RESULTS:
            query_value = payload.get("query")
            query = query_value if isinstance(query_value, str) else None

            merchant_value = payload.get("merchant")
            merchant: Merchant | None
            if isinstance(merchant_value, Merchant):
                merchant = merchant_value
            elif isinstance(merchant_value, str):
                try:
                    merchant = Merchant(merchant_value)
                except ValueError:
                    merchant = None
            else:
                merchant = None

            self._browser.navigate_to_search_results(
                session_id=session_id,
                query=query,
                merchant=merchant,
            )
            return

        if command.type == AgentCommandType.INSPECT_PRODUCT_PAGE:
            page_type_value = payload.get("page_type")
            page_type = page_type_value if isinstance(page_type_value, str) else None
            self._browser.inspect_product_page(
                session_id=session_id,
                page_type=page_type,
            )
            return

        if command.type == AgentCommandType.VERIFY_PRODUCT_VARIANT:
            self._browser.verify_product_variant(session_id=session_id)
            return

        if command.type == AgentCommandType.REVIEW_CART:
            self._browser.review_cart(session_id=session_id)
            return

        if command.type == AgentCommandType.PERFORM_CHECKOUT:
            self._browser.perform_checkout(session_id=session_id)
            return

        if command.type == AgentCommandType.HANDLE_ERROR_RECOVERY:
            error_type_value = payload.get("error_type")
            error_type = error_type_value if isinstance(error_type_value, str) else None
            self._browser.handle_error_recovery(
                session_id=session_id,
                error_type=error_type,
            )
            return

        # Non-browser commands are handled by higher layers (UI/session lifecycle).
        # No-op here by design.
        return

    def execute_many(self, session_id: UUID, commands: list[AgentCommand]) -> None:
        for command in commands:
            self.execute(session_id, command)
