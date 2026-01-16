from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.models import AsyncSessionMaker


class DbSessionMiddleware(BaseMiddleware):
    """Инъекция DB-сессии в каждый хендлер"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionMaker() as session:
            data["session"] = session
            return await handler(event, data)
