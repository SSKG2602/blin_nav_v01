from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


def build_health_payload(status: str) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.service_name,
        environment=settings.environment,
        status=status,
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return build_health_payload("ok")


@router.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return build_health_payload("live")


@router.get("/health/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    return build_health_payload("ready")
