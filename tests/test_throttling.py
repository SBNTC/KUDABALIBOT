"""
Тесты ThrottlingMiddleware.

Проверяем rate-limiting логику без реального Telegram (MagicMock для Message).
"""
import asyncio
import sys
import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middlewares.throttling import ThrottlingMiddleware  # direct import, bypasses middlewares/__init__


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_message(user_id: int) -> MagicMock:
    """Создаёт фейковый aiogram Message с нужным from_user.id."""
    from aiogram.types import Message
    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    return msg


async def _call(mw: ThrottlingMiddleware, msg, handler=None):
    if handler is None:
        handler = AsyncMock(return_value="ok")
    result = await mw(handler, msg, {})
    return result, handler


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestThrottlingMiddleware:
    @pytest.mark.asyncio
    async def test_first_request_passes(self):
        mw = ThrottlingMiddleware(window_sec=60, max_requests=5)
        msg = _make_message(user_id=1)
        result, handler = await _call(mw, msg)
        assert result == "ok"
        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_within_limit_passes(self):
        mw = ThrottlingMiddleware(window_sec=60, max_requests=3)
        msg = _make_message(user_id=2)
        for _ in range(3):
            result, _ = await _call(mw, msg)
            assert result == "ok"

    @pytest.mark.asyncio
    async def test_exceeds_limit_dropped(self):
        mw = ThrottlingMiddleware(window_sec=60, max_requests=3)
        msg = _make_message(user_id=3)
        # 3 allowed
        for _ in range(3):
            await _call(mw, msg)
        # 4th must be dropped (None)
        result, handler = await _call(mw, msg)
        assert result is None
        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_different_users_independent(self):
        mw = ThrottlingMiddleware(window_sec=60, max_requests=1)
        msg_a = _make_message(user_id=10)
        msg_b = _make_message(user_id=11)

        result_a, _ = await _call(mw, msg_a)
        result_b, _ = await _call(mw, msg_b)
        assert result_a == "ok"
        assert result_b == "ok"

        # Both now at limit — next request for each dropped
        dropped_a, h_a = await _call(mw, msg_a)
        dropped_b, h_b = await _call(mw, msg_b)
        assert dropped_a is None
        assert dropped_b is None

    @pytest.mark.asyncio
    async def test_window_expiry_allows_again(self):
        mw = ThrottlingMiddleware(window_sec=1, max_requests=1)
        msg = _make_message(user_id=20)

        # First request — ok
        result, _ = await _call(mw, msg)
        assert result == "ok"

        # Second immediately — dropped
        dropped, _ = await _call(mw, msg)
        assert dropped is None

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should pass again
        result, _ = await _call(mw, msg)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_non_message_event_passes_through(self):
        from aiogram.types import CallbackQuery
        mw = ThrottlingMiddleware(window_sec=60, max_requests=1)
        non_msg = MagicMock(spec=CallbackQuery)  # not a Message
        handler = AsyncMock(return_value="callback_ok")
        result = await mw(handler, non_msg, {})
        assert result == "callback_ok"
        handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_message_without_user_passes_through(self):
        from aiogram.types import Message
        mw = ThrottlingMiddleware(window_sec=60, max_requests=1)
        msg = MagicMock(spec=Message)
        msg.from_user = None
        handler = AsyncMock(return_value="anon_ok")
        result = await mw(handler, msg, {})
        assert result == "anon_ok"
