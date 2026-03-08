from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "blindnav-browser-runtime"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    PORT: int = 8200
    LOG_LEVEL: str = "INFO"
    ALLOW_FINAL_PURCHASE_AUTOMATION: bool = False


settings = Settings()
