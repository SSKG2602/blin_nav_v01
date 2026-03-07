from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    status: str


@router.get("/live", response_model=HealthStatus)
def health_live() -> HealthStatus:
    return HealthStatus(status="live")


@router.get("/ready", response_model=HealthStatus)
def health_ready() -> HealthStatus:
    return HealthStatus(status="ready")

