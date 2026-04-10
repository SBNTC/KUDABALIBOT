"""
Централизованная настройка логирования.

Использование:
    from logging_config import setup_logging
    setup_logging()  # вызвать один раз в точке входа (bot.py)
"""
import logging
import logging.config
import sys


def setup_logging(level: str = "INFO") -> None:
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "standard",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        # Уменьшаем шум от внешних библиотек
        "loggers": {
            "aiogram": {"level": "WARNING"},
            "aiosqlite": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
            "telethon": {"level": "WARNING"},
            "apscheduler": {"level": "INFO"},
            "playwright": {"level": "WARNING"},
        },
    }
    logging.config.dictConfig(config)
