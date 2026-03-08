from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.live import router as live_router
from app.api.routes.session import router as session_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(session_router)
api_router.include_router(agent_router)
api_router.include_router(live_router)

__all__ = ["api_router"]
