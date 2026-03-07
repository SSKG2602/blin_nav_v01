from functools import lru_cache
from os import getenv

from pydantic import BaseModel, Field


class Settings(BaseModel):
    service_name: str = Field(default="blindnav-api")
    environment: str = Field(default="local")
    frontend_origin: str = Field(default="http://localhost:3100")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8100)
    redis_url: str = Field(default="redis://localhost:6379/0")
    database_url: str = Field(
        default="postgresql+psycopg://blindnav:blindnav@localhost:5432/blindnav"
    )
    product_wake_name: str = Field(default="Luminar")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        service_name=getenv("SERVICE_NAME", "blindnav-api"),
        environment=getenv("ENVIRONMENT", "local"),
        frontend_origin=getenv("FRONTEND_ORIGIN", "http://localhost:3100"),
        api_host=getenv("API_HOST", "0.0.0.0"),
        api_port=int(getenv("BACKEND_PORT", "8100")),
        redis_url=getenv("REDIS_URL", "redis://localhost:6379/0"),
        database_url=getenv(
            "DATABASE_URL",
            "postgresql+psycopg://blindnav:blindnav@localhost:5432/blindnav",
        ),
        product_wake_name=getenv("PRODUCT_WAKE_NAME", "Luminar"),
    )
