from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.redis import get_redis_client
from app.db.session import SessionLocal
from app.schemas.health import InfraChecks, ReadyStatus, ServiceStatus

router = APIRouter(tags=["health"])


def build_service_status(status: str) -> ServiceStatus:
    return ServiceStatus(
        service=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        status=status,
    )


def check_db() -> str:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "down"


def check_redis() -> str:
    try:
        client = get_redis_client()
        if client.ping():
            return "ok"
        return "down"
    except Exception:
        return "down"


def aggregate_ready_status(checks: InfraChecks) -> str:
    values = {checks.db, checks.redis}
    if values == {"ok"}:
        return "ok"
    if values == {"down"}:
        return "down"
    return "degraded"


@router.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return build_service_status("ok")


@router.get("/health/live", response_model=ServiceStatus)
def live() -> ServiceStatus:
    return build_service_status("ok")


@router.get("/health/ready", response_model=ReadyStatus)
def ready() -> ReadyStatus:
    checks = InfraChecks(db=check_db(), redis=check_redis())
    return ReadyStatus(
        service=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        status=aggregate_ready_status(checks),
        checks=checks,
    )
