from __future__ import annotations

import logging

from fastapi import FastAPI

from browser_runtime.config import settings
from browser_runtime.driver import browser_session_manager
from browser_runtime.routes import api_router

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

app = FastAPI(
    title="BlindNav Browser Runtime",
    description="Browser-runtime action service for BlindNav command execution.",
    version="0.1.0",
)
app.include_router(api_router)


@app.on_event("shutdown")
def on_shutdown() -> None:
    browser_session_manager.shutdown()
