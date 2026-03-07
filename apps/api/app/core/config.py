from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "blindnav-api"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    FRONTEND_ORIGIN: str = "http://localhost:3100"
    BACKEND_PORT: int = 8100
    DATABASE_URL: str = "postgresql+psycopg://blindnav:blindnav@localhost:5432/blindnav"
    REDIS_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"


settings = Settings()
