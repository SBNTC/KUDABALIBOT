"""
Singleton Telethon client.

Один клиент на весь lifecycle процесса — не пересоздаётся каждые N часов.
Автоматически переподключается если соединение потеряно.
"""
import logging
from telethon import TelegramClient
from config import config

logger = logging.getLogger(__name__)

_client: TelegramClient | None = None


async def get_client() -> TelegramClient:
    """Возвращает живой Telethon-клиент, при необходимости переподключает."""
    global _client
    if _client is None:
        _client = TelegramClient(
            "anon_session",
            int(config.telegram_api_id),
            config.telegram_api_hash,
        )
    if not _client.is_connected():
        await _client.start()
        logger.info("Telethon client connected")
    return _client


async def close_client() -> None:
    """Корректно закрывает соединение при shutdown."""
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
        logger.info("Telethon client disconnected")
    _client = None
