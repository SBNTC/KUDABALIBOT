"""
Collector: сканирование Telegram-чатов.

Два режима:
  1. scheduled_chat_scan()  — запускается из scheduler'а по расписанию.
  2. start_collector()      — долгоживущий процесс с real-time слушателем.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import config
from config.chats import (
    CHATS_TO_LISTEN,
    KEYWORDS_REGEX,
    STOP_WORDS,
    MIN_TEXT_LENGTH,
)
from database.models import AsyncSessionMaker, ScrapedEvent, compute_text_hash, init_db


logger = logging.getLogger(__name__)


def _passes_filters(text: str) -> bool:
    """Мусор/нерелевантное отсекаем ДО keywords."""
    if not text or len(text) < MIN_TEXT_LENGTH:
        return False
    text_lower = text.lower()
    # Стоп-слова — проверяем первыми
    if any(stop in text_lower for stop in STOP_WORDS):
        return False
    # Ключевые слова
    if not KEYWORDS_REGEX.search(text):
        return False
    return True


async def save_message(
    chat_title: str,
    link: str,
    text: str,
    msg_date: datetime | None = None,
) -> int | None:
    """Сохраняет сообщение, возвращает id или None (если дубль)."""
    text_hash = compute_text_hash(text)

    async with AsyncSessionMaker() as session:
        exists = await session.scalar(
            select(ScrapedEvent).where(ScrapedEvent.text_hash == text_hash)
        )
        if exists:
            return None

        try:
            new_event = ScrapedEvent(
                chat_title=chat_title,
                link=link,
                raw_text=text,
                text_hash=text_hash,
                status="pending",
                created_at=msg_date or datetime.now(timezone.utc),
            )
            session.add(new_event)
            await session.commit()
            await session.refresh(new_event)
            return new_event.id
        except IntegrityError:
            await session.rollback()
            return None


def _build_link(entity, message_id: int) -> str:
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"
    return f"https://t.me/c/{getattr(entity, 'id', 0)}/{message_id}"


async def _scan_entity(client: TelegramClient, entity, limit_date: datetime) -> int:
    """Сканирует один чат, возвращает число сохранённых сообщений."""
    chat_title = getattr(entity, "title", "Unknown")
    saved = 0
    try:
        async for message in client.iter_messages(
            entity, offset_date=limit_date, reverse=True, limit=200
        ):
            text = message.message or ""
            if not _passes_filters(text):
                continue

            link = _build_link(entity, message.id)
            if await save_message(chat_title, link, text, message.date):
                saved += 1
    except Exception as e:
        logger.error(f"❌ scan {chat_title}: {e}")
    return saved


async def scan_history(client: TelegramClient) -> int:
    """Сканирование диалогов, в которых мы состоим."""
    logger.info(f"🔄 Сбор истории за {config.history_days} дней...")
    limit_date = datetime.now(timezone.utc) - timedelta(days=config.history_days)

    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs.append(dialog.entity)

    count_saved = 0
    for idx, entity in enumerate(dialogs, start=1):
        logger.info(f"[{idx}/{len(dialogs)}] {getattr(entity, 'title', 'Unknown')}...")
        count_saved += await _scan_entity(client, entity, limit_date)

    logger.info(f"✅ Сохранено: {count_saved}")
    return count_saved


async def scan_target_chats(client: TelegramClient) -> int:
    """
    Сканирует список CHATS_TO_LISTEN (публичные юзернеймы), даже если мы
    не подписаны. Используется из scheduler.
    """
    logger.info(f"🔄 Сканирование {len(CHATS_TO_LISTEN)} целевых чатов...")
    limit_date = datetime.now(timezone.utc) - timedelta(days=config.history_days)

    count_saved = 0
    for chat in CHATS_TO_LISTEN:
        try:
            entity = await client.get_entity(chat.lstrip("@"))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось открыть {chat}: {e}")
            continue

        logger.info(f"📡 {getattr(entity, 'title', chat)}")
        count_saved += await _scan_entity(client, entity, limit_date)
        await asyncio.sleep(2)  # anti-flood

    logger.info(f"✅ Целевые чаты: сохранено {count_saved}")
    return count_saved


async def scheduled_chat_scan() -> int:
    """Одноразовый прогон сканера (для APScheduler)."""
    await init_db()
    client = TelegramClient(
        "anon_session", int(config.telegram_api_id), config.telegram_api_hash
    )
    await client.start()
    try:
        saved_dialogs = await scan_history(client)
        saved_targets = await scan_target_chats(client)
        return saved_dialogs + saved_targets
    finally:
        await client.disconnect()


async def start_collector():
    """Долгоживущий real-time слушатель (опционально, не обязателен)."""
    await init_db()
    client = TelegramClient(
        "anon_session", int(config.telegram_api_id), config.telegram_api_hash
    )
    await client.start()

    # Первичный сбор
    await scan_history(client)

    logger.info("🧠 Первичный анализ...")
    from services.analyzer import run_batch_analysis
    result = await run_batch_analysis()
    logger.info(f"📊 {result}")

    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs.append(dialog.entity)
    logger.info(f"📡 Real-time мониторинг {len(dialogs)} чатов...")

    @client.on(events.NewMessage(chats=dialogs))
    async def handler(event):
        text = event.message.message or ""
        chat = await event.get_chat()
        chat_title = getattr(chat, "title", "Unknown")
        link = _build_link(chat, event.message.id)

        # Отзывы о местах — пропускаем все сообщения через анализатор отзывов
        try:
            from services.reviews_analyzer import analyze_message_for_reviews
            sender = await event.get_sender()
            sender_username = getattr(sender, "username", None) or "anonymous"
            await analyze_message_for_reviews(
                text=text,
                chat_title=chat_title,
                username=sender_username,
                link=link,
                message_date=event.message.date,
            )
        except Exception as e:
            logger.debug(f"review skip: {e}")

        # События — только по keywords + фильтрам
        if not _passes_filters(text):
            return

        event_id = await save_message(chat_title, link, text, event.message.date)
        if event_id:
            logger.info(f"📥 Live: {chat_title[:30]}")
            from services.analyzer import analyze_realtime_event
            await analyze_realtime_event(event_id)

    await client.run_until_disconnected()


async def run_manual_scan():
    """Ручной прогон сбора (использует discover_* utilities)."""
    await scheduled_chat_scan()
    logger.info("✅ Ручной сбор завершён")
