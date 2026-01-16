import re
import asyncio
import logging
from services.site_parser import run_site_parser
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from config import config
from database.models import AsyncSessionMaker, ScrapedEvent, init_db, compute_text_hash
from services.analyzer import run_batch_analysis, cleanup_old_events
from services.link_checker import check_dead_links

KEYWORDS_REGEX = re.compile(
    r"(бесплатн|free entry|free|donation|донейшн|вход свободн|"
    r"нетворкинг|networking|конференц|бизнес.?завтрак|бизнес.?встреча|"
    r"вечеринк|party|dj|концерт|"
    r"розыгрыш|giveaway|конкурс|"
    r"мастер.?класс|воркшоп|workshop|"
    r"meetup|митап|встреча|"
    r"пробн\w+\s+занят|бесплатн\w+\s+(урок|занят|консультац)|"
    r"открыт\w+\s+(урок|занят|лекц)|"
    r"приглаша\w+|регистрац|записаться|"
    r"каждый\s+(понедельник|вторник|сред[у|ы]|четверг|пятниц|суббот|воскресень)|"
    r"открытый\s+микрофон|stand\s*up|стендап|"
    r"сальса|бачата|кизомба|танц|"
    r"english\s+club|разговорный\s+клуб)",
    re.IGNORECASE
)


async def save_message(chat_title: str, link: str, text: str) -> bool:
    text_hash = compute_text_hash(text)
    
    async with AsyncSessionMaker() as session:
        exists = await session.scalar(
            select(ScrapedEvent).where(ScrapedEvent.text_hash == text_hash)
        )
        if exists:
            return False
        
        try:
            new_event = ScrapedEvent(
                chat_title=chat_title,
                link=link,
                raw_text=text,
                text_hash=text_hash,
                status="pending"
            )
            session.add(new_event)
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


async def scan_history(client: TelegramClient):
    logging.info(f"🔄 Сбор истории за {config.history_days} дней...")
    
    limit_date = datetime.now(timezone.utc) - timedelta(days=config.history_days)
    
    dialogs_to_scan = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs_to_scan.append(dialog.entity)
    
    count_saved = 0
    total_chats = len(dialogs_to_scan)
    
    for idx, entity in enumerate(dialogs_to_scan):
        chat_title = getattr(entity, 'title', 'Unknown')
        username = getattr(entity, 'username', '')
        
        logging.info(f"[{idx+1}/{total_chats}] {chat_title}...")
        
        try:
            async for message in client.iter_messages(entity, offset_date=limit_date, reverse=True):
                text = message.message or ""
                
                if len(text) < 50:
                    continue
                
                if KEYWORDS_REGEX.search(text):
                    if username:
                        link = f"https://t.me/{username}/{message.id}"
                    else:
                        link = f"https://t.me/c/{entity.id}/{message.id}"
                    
                    if await save_message(chat_title, link, text):
                        count_saved += 1
        except Exception as e:
            logging.error(f"❌ {chat_title}: {e}")
    
    logging.info(f"✅ Сохранено: {count_saved}")


async def periodic_analysis():
    """Анализ каждые 6 часов, сайт каждые 12, проверка ссылок каждый час"""
    cycle = 0
    while True:
        await asyncio.sleep(3600)  # Каждый час
        cycle += 1
        
        # Каждый час — проверка мёртвых ссылок
        try:
            await check_dead_links()
        except Exception as e:
            logging.error(f"❌ Link checker: {e}")
        
        # Каждые 6 часов — анализ
        if cycle % 6 == 0:
            logging.info("⏰ Запуск периодического анализа...")
            
            from services.analyzer import cleanup_old_events, run_batch_analysis
            await cleanup_old_events()
            
            while True:
                result = await run_batch_analysis()
                logging.info(f"📊 {result}")
                if "📭" in result or "Нет новых" in result:
                    break
                await asyncio.sleep(5)
        
        # Каждые 12 часов — парсинг сайта
        if cycle % 12 == 0:
            try:
                await run_site_parser()
            except Exception as e:
                logging.error(f"❌ Site parser: {e}")


async def start_collector():
    await init_db()
    
    client = TelegramClient('anon_session', int(config.telegram_api_id), config.telegram_api_hash)
    await client.start()
    
    # Первичный сбор
    await scan_history(client)
    
    # Первичный анализ
    logging.info("🧠 Первичный анализ...")
    result = await run_batch_analysis()
    logging.info(f"📊 {result}")
    
    # Real-time мониторинг
    dialogs_to_monitor = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs_to_monitor.append(dialog.entity)
    
    logging.info(f"📡 Real-time мониторинг {len(dialogs_to_monitor)} чатов...")
    
    @client.on(events.NewMessage(chats=dialogs_to_monitor))
    async def handler(event):
        text = event.message.message or ""
        
        if len(text) < 50:
            return
        
        if KEYWORDS_REGEX.search(text):
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', 'Unknown')
            username = getattr(chat, 'username', '')
            
            if username:
                link = f"https://t.me/{username}/{event.message.id}"
            else:
                link = f"https://t.me/c/{chat.id}/{event.message.id}"
            
            if await save_message(chat_title, link, text):
                logging.info(f"📥 Live: {chat_title[:30]}")
    
    # Запуск периодического анализа в фоне
    asyncio.create_task(periodic_analysis())
    
    await client.run_until_disconnected()


async def run_manual_scan():
    await init_db()
    
    client = TelegramClient('anon_session', int(config.telegram_api_id), config.telegram_api_hash)
    await client.start()
    
    await scan_history(client)
    
    await client.disconnect()
    logging.info("✅ Ручной сбор завершён")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(start_collector())
