from __future__ import annotations

from fastapi import Depends

from app.core.config import settings
from app.tools.browser_runtime import BrowserRuntimeClient
from app.tools.executor import AgentCommandExecutor
from app.tools.http_browser_runtime import HttpBrowserRuntimeClient


def get_browser_runtime_client() -> BrowserRuntimeClient:
    return HttpBrowserRuntimeClient(base_url=settings.BROWSER_RUNTIME_BASE_URL)


def get_agent_command_executor(
    browser_client: BrowserRuntimeClient = Depends(get_browser_runtime_client),
) -> AgentCommandExecutor:
    return AgentCommandExecutor(browser_client)
