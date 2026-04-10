"""
ThrottlingMiddleware: ограничивает частоту AI-запросов на пользователя.

По умолчанию: не более 10 сообщений в минуту на user_id.
При превышении — молча игнорирует (не отправляет ответ).
"""
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

_WINDOW_SEC = 60
_MAX_REQUESTS = 10


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, window_sec: int = _WINDOW_SEC, max_requests: int = _MAX_REQUESTS) -> None:
        self._window = window_sec
        self._limit = max_requests
        # {user_id: [timestamp, ...]}
        self._history: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        if not user:
            return await handler(event, data)

        now = time.monotonic()
        history = self._history[user.id]

        # Убираем записи старше окна
        cutoff = now - self._window
        while history and history[0] < cutoff:
            history.pop(0)

        if len(history) >= self._limit:
            # Превышен лимит — тихо отбрасываем
            return None

        history.append(now)
        return await handler(event, data)
