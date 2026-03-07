from fastapi import APIRouter

from browser_runtime.routes.actions import router as actions_router
from browser_runtime.routes.health import router as health_router
from browser_runtime.routes.observation import router as observation_router

api_router = APIRouter()
api_router.include_router(actions_router)
api_router.include_router(health_router)
api_router.include_router(observation_router)

__all__ = ["api_router"]
