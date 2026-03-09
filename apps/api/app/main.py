# apps/api/app/main.py
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup if they don't exist.
    # This is safe to call repeatedly — it is a no-op for existing tables.
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception:
            if attempt == max_attempts:
                logger.exception(
                    "Database metadata initialization failed after %s attempts; starting server without crashing.",
                    max_attempts,
                )
                break
            logger.warning(
                "Database metadata initialization attempt %s/%s failed; retrying in 2 seconds.",
                attempt,
                max_attempts,
                exc_info=True,
            )
            time.sleep(2)
    yield


app = FastAPI(
    title="BlindNav API",
    description="BlindNav backend for deterministic shopping orchestration, live session control, and browser-grounded runtime integration.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
