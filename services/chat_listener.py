import os
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from sqlalchemy import text
from sqlalchemy.dialects.sqlite import insert
from database.base import async_session_maker
from database.models import Event
from services.ai_analyzer import analyze_event

logger = logging.getLogger(__name__)

# Полный список чатов из вашего старого скрипта
CHATS_TO_LISTEN = [
    '@balichatnews', '@businessmenBali', '@Balibizness', 
    '@networkers_bali', '@bali_party', '@balifm_afisha', 
    '@blizkie_eventss',
    '@balichat', '@balichatdating', '@balichatik', '@balichatnash', 
    '@networkingbali', '@voprosBali', '@baliRU', '@Peoplebali', 
    '@bali_360', '@balichatflood', '@balistop', '@baliEast', 
    '@baliUKR', '@bali_laika', '@balidating', '@plus49',
    '@artbali', '@bali_tusa', '@eventsbali', '@balievents', 
    '@baligames', '@truth_in_cinema', '@pvbali',
    '@balisp', '@balipractice', '@Balidance', '@balisoul', 
    '@baliyoga', 
    # Ссылки joinchat обрабатываются отдельно, здесь оставим юзернеймы
    '@redkinvilla', '@balimassag', '@ArtTherapyBali', 
    '@tranformationgames', 
    '@domanabali', '@domanabalichat', '@balichatarenda', 
    '@balirental', '@VillaUbud', '@bali_house', '@allAbout_Bali', 
    '@balibike', '@baliauto', '@rentcarbaliopen',
    '@balifruits', '@balifood', '@balihealth', '@RAWBali',
    '@balibc', 
    '@balida21', '@seobali', '@jobsbali', '@balimc', '@BaliManClub',
    '@indonesia_bali',
    '@balichat_woman', '@bali_woman', '@baliwomans', '@balibeauty',
    '@balirussia', '@balipackage', '@balichatmarket', 
    '@bali_baraholka', '@balisale', '@bali_sharing', 
    '@Bali_buy_sale', '@designclothing', '@balimoney',
    '@balichildren', '@roditelibali', 
    '@balifootball', '@balibasket', '@balisurfer'
]

# Ссылки, которые нельзя просто так вставить в iter_messages (нужен join)
# Пока оставим их за скобками или добавим логику вступления, если нужно.
# Telethon может работать с invite links, но это сложнее.

KEYWORDS = [
    'бесплатн', 'free', 'свободн', 'донейшн', 'donation', 'донат', 
    'оплата по сердцу', 'без оплаты', '0 руб', '0$', 'безоплатн', 'дар', 'даром',
    'pay what you want', 'открытый урок', 'открытая встреча', 'день открытых дверей',
    'мастер-класс', 'лекция', 'семинар', 'воркшоп', 'практика', 'кинопоказ', 
    'просмотр', 'игра', 'медитация', 'йога', 'yoga', 'ecstatic', 'dance',
    'встреча', 'собрание', 'нетворк', 'network', 'speaking club', 'breakfast', 'завтрак',
    'разговорный клуб', 'языковой обмен', 'language exchange',
    'приглашаем', 'ждем вас', 'собираемся', 'анонс', 'будет проходить',
    'состоится', 'приходите', 'залетайте', 'всех желающих'
]

STOP_WORDS = [
    'ищу', 'сниму', 'аренда', 'сдам', 
    'такси', 'обмен валют', 'виза', 'visa',
    'продам байк', 'продам шлем', 'сдам виллу',
    'куплю', 'продам', 'iphone', 'macbook'
]

SCAN_INTERVAL_HOURS = 6
LOOKBACK_HOURS = 24 # Увеличим глубину сканирования при старте

client = TelegramClient(
    'server_listener_session', 
    int(os.getenv("API_ID")), 
    os.getenv("API_HASH")
)

async def _process_and_save(chat_title, link, text_content, date):
    """Единая функция обработки и сохранения события"""
    if not text_content: return
    text_lower = text_content.lower()
    
    if any(s in text_lower for s in STOP_WORDS): return
    if not any(k in text_lower for k in KEYWORDS): return

    # Проверка на дубликаты
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT 1 FROM events WHERE link = :link"), 
            {"link": link}
        )
        if result.scalar():
            return

    logger.info(f"🔎 Analysing: {chat_title} | {date}")
    
    # AI Анализ (теперь с fallback)
    ai_result = await analyze_event(text_content)
    
    # Сохранение
    async with async_session_maker() as session:
        stmt = insert(Event).values(
            chat_title=chat_title,
            text=text_content,
            link=link,
            category=ai_result.get('category', 'unknown'),
            summary=ai_result.get('summary', 'Событие'),
            created_at=date.replace(tzinfo=None)
        ).on_conflict_do_nothing(index_elements=['link'])
        
        await session.execute(stmt)
        await session.commit()
    
    logger.info(f"💾 Saved [{ai_result.get('category')}]: {ai_result.get('summary')}")

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Обработчик realtime сообщений (из тех чатов, где мы состоим)"""
    try:
        text = event.message.text or ""
        if not text: return

        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', str(chat.id))
        username = getattr(chat, 'username', None)
        
        if username:
            link = f"https://t.me/{username}/{event.message.id}"
        else:
            link = f"https://t.me/c/{chat.id}/{event.message.id}"

        msg_date = event.message.date or datetime.now(timezone.utc)
        await _process_and_save(chat_title, link, text, msg_date)
    except Exception as e:
        logger.error(f"Realtime handler error: {e}")

async def scan_recent_messages():
    """Сканирует историю целевых чатов"""
    logger.info("🔄 Starting periodic scan...")
    cutoff_date = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    
    messages_scanned = 0
    
    # Сначала пробежимся по списку целевых чатов
    # Telethon позволяет итерироваться по строкам-юзернеймам
    for chat_input in CHATS_TO_LISTEN:
        try:
            # Убираем лишнее из ссылки, если есть
            entity = chat_input.replace('https://t.me/', '').replace('@', '')
            
            # Получаем объект канала/чата (если мы там не состоим, это может упасть)
            # Но iter_messages умеет работать с юзернеймами публичных каналов даже без подписки
            try:
                chat_entity = await client.get_entity(entity)
                chat_title = chat_entity.title
            except Exception:
                chat_title = entity # Если не удалось получить название
            
            logger.info(f"📡 Scanning: {chat_title}")

            async for message in client.iter_messages(entity, offset_date=cutoff_date, reverse=True):
                messages_scanned += 1
                text = message.text or ""
                if not text: continue
                
                # Формируем ссылку
                # Для публичных каналов лучше использовать юзернейм
                if hasattr(message.chat, 'username') and message.chat.username:
                    link = f"https://t.me/{message.chat.username}/{message.id}"
                else:
                    link = f"https://t.me/c/{message.chat_id}/{message.id}"
                
                await _process_and_save(chat_title, link, text, message.date)
            
            # Пауза, чтобы телеграм не забанил за флуд
            await asyncio.sleep(2) 
            
        except Exception as e:
            logger.error(f"Error scanning chat {chat_input}: {e}")
            continue
            
    logger.info(f"✅ Scan finished. Scanned {messages_scanned} messages.")

async def scheduler_loop():
    while True:
        await scan_recent_messages()
        logger.info(f"💤 Sleeping for {SCAN_INTERVAL_HOURS} hours...")
        await asyncio.sleep(SCAN_INTERVAL_HOURS * 3600)

async def start_telethon():
    logger.info("🚀 Starting Telethon Client...")
    await client.start()
    logger.info("✅ Telethon connected!")
    asyncio.create_task(scheduler_loop())
