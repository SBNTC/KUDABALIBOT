import re
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from config import config
from database.models import AsyncSessionMaker, ScrapedEvent, compute_text_hash, init_db

KEYWORDS_REGEX = re.compile(
    r"(бесплатн|free entry|free|donation|донейшн|вход свободн|"
    r"нетворкинг|networking|конференц|бизнес.?завтрак|бизнес.?встреча|"
    r"вечеринк|party|dj|концерт|"
    r"мастер.?класс|воркшоп|workshop|"
    r"meetup|митап|встреча|"
    r"пробн\w+\s+занят|бесплатн\w+\s+(урок|занят|консультац)|"
    r"открыт\w+\s+(урок|занят|лекц)|"
    r"приглаша\w+|регистрац|записаться|"
    r"открытый\s+микрофон|stand\s*up|стендап|"
    r"сальса|бачата|кизомба|танц|"
    r"english\s+club|разговорный\s+клуб)",
    re.IGNORECASE
)


async def save_message(chat_title: str, link: str, text: str, msg_date: datetime = None) -> int | None:
    """Сохраняет сообщение, возвращает ID или None"""
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
                created_at=msg_date or datetime.now(timezone.utc)
            )
            session.add(new_event)
            await session.commit()
            await session.refresh(new_event)
            return new_event.id
        except IntegrityError:
            await session.rollback()
            return None


async def scan_history(client: TelegramClient):
    """Сканирование истории чатов"""
    logging.info(f"🔄 Сбор истории за {config.history_days} дней...")
    
    limit_date = datetime.now(timezone.utc) - timedelta(days=config.history_days)
    
    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs.append(dialog.entity)
    
    count_saved = 0
    total_chats = len(dialogs)
    
    for idx, entity in enumerate(dialogs):
        chat_title = getattr(entity, 'title', 'Unknown')
        username = getattr(entity, 'username', '')
        
        logging.info(f"[{idx+1}/{total_chats}] {chat_title}...")
        
        try:
            async for message in client.iter_messages(entity, offset_date=limit_date, reverse=True, limit=100):
                text = message.message or ""
                if len(text) < 50:
                    continue
                
                if KEYWORDS_REGEX.search(text):
                    link = f"https://t.me/{username}/{message.id}" if username else f"https://t.me/c/{entity.id}/{message.id}"
                    
                    if await save_message(chat_title, link, text, message.date):
                        count_saved += 1
        except Exception as e:
            logging.error(f"❌ {chat_title}: {e}")
    
    logging.info(f"✅ Сохранено: {count_saved}")


async def start_collector():
    """Запуск коллектора с realtime мониторингом"""
    await init_db()
    
    client = TelegramClient('anon_session', int(config.telegram_api_id), config.telegram_api_hash)
    await client.start()
    
    # Первичный сбор
    await scan_history(client)
    
    # Первичный анализ → сразу approved
    logging.info("🧠 Первичный анализ...")
    from services.analyzer import run_batch_analysis
    result = await run_batch_analysis(auto_approve=True)
    logging.info(f"📊 {result}")
    
    # Real-time мониторинг
    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs.append(dialog.entity)
    
    logging.info(f"📡 Real-time мониторинг {len(dialogs)} чатов...")
    
    @client.on(events.NewMessage(chats=dialogs))
    async def handler(event):
        text = event.message.message or ""
        if len(text) < 50:
            return
        
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Unknown')
        chat_username = getattr(chat, 'username', '')
        link = f"https://t.me/{chat_username}/{event.message.id}" if chat_username else f"https://t.me/c/{chat.id}/{event.message.id}"
        
        # Анализ отзывов о местах (для всех сообщений)
        try:
            from services.reviews_analyzer import analyze_message_for_reviews
            sender = await event.get_sender()
            sender_username = getattr(sender, 'username', None) or 'anonymous'
            await analyze_message_for_reviews(
                text=text,
                chat_title=chat_title,
                username=sender_username,
                link=link,
                message_date=event.message.date
            )
        except Exception as e:
            logging.debug(f"Review analyze skip: {e}")
        
        # Анализ событий (только по ключевым словам)
        if KEYWORDS_REGEX.search(text):
            event_id = await save_message(chat_title, link, text, event.message.date)
            if event_id:
                logging.info(f"📥 Live: {chat_title[:30]}")
                from services.analyzer import analyze_realtime_event
                await analyze_realtime_event(event_id)
    
    await client.run_until_disconnected()


async def run_manual_scan():
    """Ручной сбор"""
    await init_db()
    client = TelegramClient('anon_session', int(config.telegram_api_id), config.telegram_api_hash)
    await client.start()
    await scan_history(client)
    await client.disconnect()
    logging.info("✅ Ручной сбор завершён")


# Добавить в обработчик новых сообщений:
# from services.reviews_analyzer import analyze_message_for_reviews
#
# В handler после сохранения события:
# await analyze_message_for_reviews(
#     text=event.message.text,
#     chat_title=chat_title,
#     username=event.message.sender.username if event.message.sender else None,
#     link=f"https://t.me/{chat_title}/{event.message.id}",
#     message_date=event.message.date
# )
