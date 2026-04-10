"""
Интеграционные тесты бота (Level 2).

Используют настоящий aiogram Dispatcher + fake Update.
Bot API-вызовы перехватываются CapturingSession — реальных HTTP нет.
DeepSeek/Telethon замокированы там, где нужны.

Покрывает:
  - ThrottlingMiddleware в контексте реального Dispatcher'а
  - IsAdmin-фильтр: блокировка не-администраторов
  - /help → ответ с ожидаемым текстом
  - /stats → ответ с данными из тестовой БД
  - /clean → удаление устаревших событий + ответ
"""
import datetime

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from tests.conftest import ADMIN_ID, REGULAR_USER_ID, make_update


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_dp() -> Dispatcher:
    """Каждый тест получает изолированный Dispatcher без глобальных роутеров."""
    return Dispatcher(storage=MemoryStorage())


def _sent_texts(bot) -> list[str]:
    return bot.session.sent_texts()


def _make_admin_router() -> Router:
    """
    Создаёт свежий Router с admin-хэндлерами каждый раз.

    admin_router в handlers/admin_panel.py — модульный синглтон:
    однажды включённый в Dispatcher, он не может быть включён в другой.
    Поэтому мы берём функции хэндлеров напрямую и регистрируем их на
    новом Router'е, сохраняя логику маршрутизации.
    """
    from config import config
    import handlers.admin_panel as adm

    router = Router()
    router.message.filter(
        lambda m: m.from_user is not None and m.from_user.id == config.admin_id
    )
    router.message(Command("help"))(adm.cmd_help)
    router.message(Command("stats"))(adm.cmd_stats)
    router.message(Command("clean"))(adm.cmd_clean_old)
    router.message(Command("dedup"))(adm.cmd_dedup_exact)
    router.message(Command("dedup_fuzzy"))(adm.cmd_dedup_fuzzy)
    return router


def _admin_dp() -> Dispatcher:
    dp = _fresh_dp()
    dp.include_router(_make_admin_router())
    return dp


# ---------------------------------------------------------------------------
# Throttling Middleware
# ---------------------------------------------------------------------------

class TestThrottlingInDispatcher:
    """Проверяем, что middleware реально блокирует лишние запросы в dp."""

    async def test_within_limit_all_handled(self, bot):
        from middlewares.throttling import ThrottlingMiddleware

        dp = _fresh_dp()
        dp.message.middleware(ThrottlingMiddleware(window_sec=60, max_requests=3))

        handled = []

        @dp.message()
        async def echo(message):
            handled.append(message.text)

        for i in range(3):
            await dp.feed_update(bot, make_update("hi", user_id=1, update_id=i + 1))

        assert len(handled) == 3

    async def test_exceeds_limit_extra_dropped(self, bot):
        from middlewares.throttling import ThrottlingMiddleware

        dp = _fresh_dp()
        dp.message.middleware(ThrottlingMiddleware(window_sec=60, max_requests=2))

        handled = []

        @dp.message()
        async def echo(message):
            handled.append(message.text)

        for i in range(4):
            await dp.feed_update(bot, make_update("hi", user_id=2, update_id=i + 1))

        assert len(handled) == 2  # 3-й и 4-й отброшены

    async def test_different_users_independent_limits(self, bot):
        from middlewares.throttling import ThrottlingMiddleware

        dp = _fresh_dp()
        dp.message.middleware(ThrottlingMiddleware(window_sec=60, max_requests=1))

        user_a_count = 0
        user_b_count = 0

        @dp.message()
        async def echo(message):
            nonlocal user_a_count, user_b_count
            if message.from_user.id == 10:
                user_a_count += 1
            else:
                user_b_count += 1

        await dp.feed_update(bot, make_update("hi", user_id=10, update_id=1))
        await dp.feed_update(bot, make_update("hi", user_id=20, update_id=2))
        # Второй запрос от каждого — отброшен
        await dp.feed_update(bot, make_update("hi", user_id=10, update_id=3))
        await dp.feed_update(bot, make_update("hi", user_id=20, update_id=4))

        assert user_a_count == 1
        assert user_b_count == 1


# ---------------------------------------------------------------------------
# IsAdmin filter
# ---------------------------------------------------------------------------

class TestIsAdminFilter:
    """Проверяем, что admin-роутер недоступен для обычных пользователей."""

    async def test_non_admin_gets_no_response(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/help", user_id=REGULAR_USER_ID))
        assert _sent_texts(bot) == []

    async def test_admin_gets_response(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/help", user_id=ADMIN_ID))
        texts = _sent_texts(bot)
        assert len(texts) == 1
        assert "Админ-команды" in texts[0]

    async def test_non_admin_blocked_for_stats(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/stats", user_id=REGULAR_USER_ID))
        assert _sent_texts(bot) == []


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

class TestCmdHelp:
    async def test_help_contains_sections(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/help", user_id=ADMIN_ID))
        texts = _sent_texts(bot)
        assert len(texts) == 1
        text = texts[0]
        assert "Управление" in text
        assert "Очистка" in text
        assert "/admin" in text
        assert "/review" in text
        assert "/dedup" in text

    async def test_help_lists_all_commands(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/help", user_id=ADMIN_ID))
        text = _sent_texts(bot)[0]
        for cmd in ["/clean", "/stats", "/reload_kb", "/help"]:
            assert cmd in text, f"Expected {cmd} in help text"


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

class TestCmdStats:
    async def test_stats_empty_db(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/stats", user_id=ADMIN_ID))
        texts = _sent_texts(bot)
        assert len(texts) == 1
        text = texts[0]
        assert "Статистика" in text
        assert "Всего событий" in text

    async def test_stats_counts_correctly(self, bot, db):
        from database.models import ScrapedEvent, compute_text_hash
        from data.statuses import EventStatus

        # 2 pending + 1 approved
        async with db() as session:
            for i, status in enumerate([
                EventStatus.PENDING,
                EventStatus.PENDING,
                EventStatus.APPROVED,
            ]):
                ev = ScrapedEvent(
                    chat_title="c",
                    link=f"https://t.me/c/{i}",
                    raw_text=f"text_{i}",
                    text_hash=compute_text_hash(f"text_{i}"),
                    status=status,
                )
                session.add(ev)
            await session.commit()

        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/stats", user_id=ADMIN_ID))
        text = _sent_texts(bot)[0]
        # Всего 3 события
        assert "3" in text
        assert "Опубликовано" in text


# ---------------------------------------------------------------------------
# /clean
# ---------------------------------------------------------------------------

class TestCmdClean:
    async def test_clean_removes_old_review_events(self, bot, db):
        from database.models import ScrapedEvent, compute_text_hash
        from data.statuses import EventStatus
        from sqlalchemy import select

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)

        async with db() as session:
            old = ScrapedEvent(
                chat_title="c", link="https://t.me/1",
                raw_text="old event", text_hash=compute_text_hash("old event"),
                status=EventStatus.REVIEW, event_date=yesterday,
            )
            future = ScrapedEvent(
                chat_title="c", link="https://t.me/2",
                raw_text="future event", text_hash=compute_text_hash("future event"),
                status=EventStatus.REVIEW, event_date=tomorrow,
            )
            pending_no_date = ScrapedEvent(
                chat_title="c", link="https://t.me/3",
                raw_text="pending no date", text_hash=compute_text_hash("pending no date"),
                status=EventStatus.PENDING,
            )
            session.add_all([old, future, pending_no_date])
            await session.commit()
            old_id = old.id
            future_id = future.id

        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/clean", user_id=ADMIN_ID))
        texts = _sent_texts(bot)
        assert len(texts) == 1
        assert "Удалено 1" in texts[0]

        async with db() as session:
            remaining = (await session.execute(select(ScrapedEvent))).scalars().all()
        remaining_ids = {e.id for e in remaining}
        assert old_id not in remaining_ids
        assert future_id in remaining_ids

    async def test_clean_nothing_to_remove(self, bot, db):
        dp = _admin_dp()
        await dp.feed_update(bot, make_update("/clean", user_id=ADMIN_ID))
        text = _sent_texts(bot)[0]
        assert "Удалено 0" in text
