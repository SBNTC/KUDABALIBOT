"""
Фикстуры для тестов.

Env vars выставляются ДО любых импортов проекта — pydantic-settings требует
их при инстанциировании Settings() на уровне модуля.
"""
import datetime
import os
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Dummy env vars — выставить до импортов проекта
# ---------------------------------------------------------------------------
_DUMMY_ENV = {
    "BOT_TOKEN": "123456789:AABBCCDDAABBCCDDAABBCCDDAABBCCDDAAB",
    "TELEGRAM_API_ID": "12345",
    "TELEGRAM_API_HASH": "deadbeefdeadbeefdeadbeefdeadbeef",
    "DEEPSEEK_API_KEY": "sk-test-dummy-key",
    "ADMIN_ID": "999999",
}
for _key, _val in _DUMMY_ENV.items():
    os.environ.setdefault(_key, _val)

# ---------------------------------------------------------------------------
# Константы, удобные в тестах
# ---------------------------------------------------------------------------
ADMIN_ID = int(_DUMMY_ENV["ADMIN_ID"])
REGULAR_USER_ID = 111111
BOT_TOKEN = _DUMMY_ENV["BOT_TOKEN"]


# ---------------------------------------------------------------------------
# Хелпер: fake aiogram Update с сообщением
# ---------------------------------------------------------------------------
def make_update(
    text: str,
    user_id: int = REGULAR_USER_ID,
    chat_id: Optional[int] = None,
    update_id: int = 1,
    is_bot: bool = False,
):
    """Строит aiogram Update с одним Message без обращения к Telegram API."""
    from aiogram.types import Update, Message, User, Chat

    chat_id = chat_id or user_id
    user = User(id=user_id, is_bot=is_bot, first_name="Test", username="testuser")
    chat = Chat(id=chat_id, type="private")
    message = Message(
        message_id=update_id,
        date=datetime.datetime.now(datetime.timezone.utc),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=update_id, message=message)


# ---------------------------------------------------------------------------
# CapturingSession: перехватывает все исходящие API-вызовы бота
# ---------------------------------------------------------------------------
class CapturingSession:
    """
    Подставляется вместо AiohttpSession.
    Все исходящие методы (SendMessage, EditMessageText, …) складываются
    в self.calls — реальных HTTP-запросов не делает.
    """

    def __init__(self):
        self.calls: list = []

    # BaseSession.__call__ делегирует сюда через middleware-цепочку.
    # Мы реализуем именно __call__, чтобы перехватить до любых middleware.
    async def __call__(self, bot, method, timeout=None):
        self.calls.append(method)
        return self._build_response(method)

    def _build_response(self, method) -> Any:
        """Возвращает минимально корректный объект для каждого типа метода."""
        from aiogram.methods import SendMessage, EditMessageText, AnswerCallbackQuery, DeleteMessage

        if isinstance(method, (SendMessage, EditMessageText)):
            msg = MagicMock()
            msg.message_id = len(self.calls)
            msg.text = getattr(method, "text", "") or ""
            msg.chat = MagicMock(id=getattr(method, "chat_id", 0))
            msg.from_user = None
            msg.date = datetime.datetime.now(datetime.timezone.utc)
            return msg

        if isinstance(method, AnswerCallbackQuery):
            return True

        if isinstance(method, DeleteMessage):
            return True

        # Fallback для любых прочих методов
        return True

    # Нужен для совместимости с Bot, который вызывает session.close()
    async def close(self):
        pass

    # Вспомогательный метод: тексты всех SendMessage в порядке отправки
    def sent_texts(self) -> list[str]:
        from aiogram.methods import SendMessage, EditMessageText
        return [
            getattr(m, "text", "") or ""
            for m in self.calls
            if isinstance(m, (SendMessage, EditMessageText))
        ]


# ---------------------------------------------------------------------------
# Фикстура: bot с перехватом API-вызовов
# ---------------------------------------------------------------------------
@pytest.fixture
def bot():
    """
    aiogram Bot, который не делает реальных HTTP-запросов.
    bot.session — это CapturingSession; все вызовы доступны через bot.session.calls.
    """
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    session = CapturingSession()
    b = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    return b


# ---------------------------------------------------------------------------
# Фикстуры: БД в памяти (SQLite :memory:)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_engine():
    """
    Изолированный async SQLite-движок в памяти — один на тест.

    StaticPool гарантирует, что все обращения AsyncSessionMaker идут
    через одно соединение (и одну in-memory БД). Создаётся заново для
    каждого теста → полная изоляция без ручной очистки таблиц.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool
    from database.models import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine, monkeypatch):
    """
    Патчит AsyncSessionMaker во всех модулях проекта, заменяя его
    session-мейкером над тестовой БД.
    Возвращает session_maker для прямого создания сессий в тестах.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(db_engine, expire_on_commit=False)

    _patch_targets = [
        "database.session.AsyncSessionMaker",
        "services.collector.AsyncSessionMaker",
        "services.dedup.AsyncSessionMaker",
        "services.reviews_analyzer.AsyncSessionMaker",
        "services.analyzer.AsyncSessionMaker",
        "handlers.admin_panel.AsyncSessionMaker",
        "handlers.user.start.AsyncSessionMaker",
        "middlewares.db.AsyncSessionMaker",
        "dialogs.admin.AsyncSessionMaker",
        "dialogs.admin_review.AsyncSessionMaker",
        "database.requests.AsyncSessionMaker",
    ]
    for target in _patch_targets:
        try:
            monkeypatch.setattr(target, session_maker)
        except (AttributeError, ImportError):
            pass  # модуль не импортирован или отсутствует зависимость

    return session_maker
