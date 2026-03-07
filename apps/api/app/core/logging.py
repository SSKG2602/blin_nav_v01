import logging
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    log_level = settings.LOG_LEVEL.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {"level": log_level, "handlers": ["default"]},
        }
    )
