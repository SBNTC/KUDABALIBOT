"""
Скрипт автоматического поиска и вступления в новые чаты Бали
Улучшенная версия: больше сообщений, связывание username↔invite, статистика
"""
import asyncio
import random
import logging
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.tl.types import Channel, User
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, ChannelPrivateError, InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError
from sqlalchemy import select

from config import config
from database.models import AsyncSessionMaker, MonitoredChat, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

SEARCH_KEYWORDS = [
    "бали", "bali", "баличат", "balichat",
    "убуд", "ubud", "чангу", "canggu",
    "семиньяк", "seminyak", "индонезия", "indonesia",
    "нетворкинг", "networking", "афиша", "events"
]

INVITE_LINK_REGEX = re.compile(
    r'(?:https?://)?(?:www\.)?t(?:elegram)?\.(?:me|dog)/(?:\+|joinchat/)([\w-]+)',
    re.IGNORECASE
)

# Статистика
stats = {
    "found_usernames": 0,
    "found_invites": 0,
    "skipped_bots": 0,
    "skipped_private": 0,
    "joined_channels": 0,
    "joined_invites": 0,
    "errors": 0
}


async def get_existing_chats() -> set:
    """Получить список уже известных чатов"""
    async with AsyncSessionMaker() as session:
        result = await session.execute(select(MonitoredChat.chat_id))
        return {row[0] for row in result.all()}


async def save_chat(chat_id: str, chat_title: str, is_member: bool = False):
    """Сохранить новый чат в БД"""
    async with AsyncSessionMaker() as session:
        exists = await session.scalar(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        if not exists:
            new_chat = MonitoredChat(
                chat_id=chat_id,
                chat_title=chat_title,
                is_member=is_member
            )
            session.add(new_chat)
            await session.commit()
            logging.info(f"💾 {chat_title}")
            return True
        return False


async def is_public_channel(client: TelegramClient, username: str) -> tuple:
    """Проверить, является ли username публичным каналом"""
    try:
        entity = await client.get_entity(username)
        
        if isinstance(entity, User):
            stats["skipped_bots"] += 1
            return False, None, None
        
        if not isinstance(entity, Channel):
            stats["skipped_private"] += 1
            return False, None, None
        
        if entity.username is None:
            stats["skipped_private"] += 1
            return False, None, None
        
        return True, entity, entity.title
    
    except Exception:
        stats["errors"] += 1
        return False, None, None


async def extract_invite_links(client: TelegramClient, existing_chats: set) -> dict:
    """Извлечь invite links из сообщений (500 последних) + связать с @username"""
    logging.info("🔗 Глубокое сканирование на invite links (500 сообщений/чат)...")
    
    limit_date = datetime.now(timezone.utc) - timedelta(days=10)
    discovered = {}  # {invite_hash: {"chat_name": "...", "mentioned_usernames": [...]}}
    
    async for dialog in client.iter_dialogs():
        if not (dialog.is_group or dialog.is_channel):
            continue
            
        try:
            async for message in client.iter_messages(dialog.entity, limit=500, offset_date=limit_date):
                if not message.text:
                    continue
                
                text_lower = message.text.lower()
                
                # Проверяем наличие ключевых слов Бали
                if not any(kw in text_lower for kw in SEARCH_KEYWORDS):
                    continue
                
                # Ищем invite links
                matches = INVITE_LINK_REGEX.findall(message.text)
                for invite_hash in matches:
                    if invite_hash not in discovered:
                        # Ищем упомянутые @username в том же сообщении
                        mentioned = re.findall(r'@(\w+)', message.text)
                        mentioned = [u for u in mentioned if not u.endswith('bot')]
                        
                        discovered[invite_hash] = {
                            "chat_name": dialog.name,
                            "mentioned_usernames": mentioned
                        }
                        
                        mention_info = f" (упомянуты: {', '.join(['@' + u for u in mentioned])})" if mentioned else ""
                        logging.info(f"   🔗 {invite_hash[:15]}... из {dialog.name}{mention_info}")
        
        except Exception:
            pass
    
    return discovered


async def discover_chats_from_dialogs(client: TelegramClient, existing_chats: set) -> list:
    """Найти @username из упоминаний (500 последних сообщений)"""
    logging.info("🔍 Глубокое сканирование @username (500 сообщений/чат)...")
    
    limit_date = datetime.now(timezone.utc) - timedelta(days=10)
    discovered = []
    
    async for dialog in client.iter_dialogs():
        if not (dialog.is_group or dialog.is_channel):
            continue
            
        try:
            async for message in client.iter_messages(dialog.entity, limit=500, offset_date=limit_date):
                if not message.text:
                    continue
                
                words = message.text.split()
                for word in words:
                    if word.startswith('@') and len(word) > 2:
                        username = word[1:].lower().rstrip(',.!?;:')
                        
                        # Пропускаем ботов
                        if username.endswith('bot'):
                            continue
                        
                        if any(kw in username for kw in SEARCH_KEYWORDS):
                            if username not in existing_chats and username not in discovered:
                                discovered.append(username)
                                stats["found_usernames"] += 1
        
        except Exception:
            pass
    
    return discovered


async def join_channel(client: TelegramClient, username: str) -> tuple:
    """Вступить ТОЛЬКО в публичный канал"""
    try:
        is_public, entity, title = await is_public_channel(client, username)
        
        if not is_public:
            return False, None, None
        
        logging.info(f"🔗 @{username}...")
        
        try:
            await client(JoinChannelRequest(entity))
            logging.info(f"   ✅ Вступил: {title}")
            stats["joined_channels"] += 1
            return True, entity.username, title
        
        except UserAlreadyParticipantError:
            logging.info(f"   ℹ️ Уже участник")
            stats["joined_channels"] += 1
            return True, entity.username, title
    
    except FloodWaitError as e:
        logging.error(f"   ⏳ FloodWait: {e.seconds} сек")
        stats["errors"] += 1
        await asyncio.sleep(e.seconds)
        return False, None, None
    
    except Exception as e:
        stats["errors"] += 1
        return False, None, None


async def join_by_invite_link(client: TelegramClient, invite_hash: str, meta: dict) -> tuple:
    """Вступить по invite link"""
    try:
        mentioned = meta.get("mentioned_usernames", [])
        mention_str = f" (@{mentioned[0]} и др.)" if mentioned else ""
        
        logging.info(f"🔗 Invite {invite_hash[:15]}...{mention_str}")
        
        # Проверяем инфо
        try:
            chat_info = await client(CheckChatInviteRequest(hash=invite_hash))
            chat_title = getattr(chat_info, 'title', 'Unknown')
        except:
            chat_title = "Unknown"
        
        # Вступаем
        result = await client(ImportChatInviteRequest(hash=invite_hash))
        
        if hasattr(result, 'chats') and result.chats:
            chat = result.chats[0]
            chat_id = str(chat.id)
            chat_title = chat.title
            
            logging.info(f"   ✅ Вступил: {chat_title}")
            stats["joined_invites"] += 1
            return True, chat_id, chat_title
        else:
            stats["joined_invites"] += 1
            return True, invite_hash, chat_title
    
    except FloodWaitError as e:
        logging.error(f"   ⏳ FloodWait: {e.seconds} сек")
        stats["errors"] += 1
        await asyncio.sleep(e.seconds)
        return False, None, None
    
    except UserAlreadyParticipantError:
        logging.info(f"   ℹ️ Уже участник")
        stats["joined_invites"] += 1
        return True, invite_hash, chat_title
    
    except (InviteHashExpiredError, InviteHashInvalidError):
        logging.warning(f"   ⏰ Устарел")
        stats["errors"] += 1
        return False, None, None
    
    except Exception as e:
        stats["errors"] += 1
        return False, None, None


async def scan_new_chats(client: TelegramClient):
    """Повторное сканирование с новыми чатами"""
    from services.collector import scrape_history
    
    logging.info("\n🔄 === ПОВТОРНОЕ СКАНИРОВАНИЕ С НОВЫМИ ЧАТАМИ ===")
    await scrape_history(client)


async def main():
    logging.info("🚀 === ЗАПУСК АГРЕССИВНОГО СБОРЩИКА ЧАТОВ ===\n")
    
    await init_db()
    
    client = TelegramClient(
        'discovery_session',
        config.telegram_api_id,
        config.telegram_api_hash
    )
    await client.start()
    
    existing_chats = await get_existing_chats()
    logging.info(f"📊 Уже отслеживается: {len(existing_chats)}\n")
    
    # === ЭТАП 1: ПОИСК ===
    discovered_usernames = await discover_chats_from_dialogs(client, existing_chats)
    discovered_invites = await extract_invite_links(client, existing_chats)
    
    stats["found_invites"] = len(discovered_invites)
    
    # Фильтруем username на публичность
    logging.info(f"\n🔍 Проверяю {len(discovered_usernames)} username на публичность...")
    public_channels = []
    
    for username in discovered_usernames:
        is_public, entity, title = await is_public_channel(client, username)
        if is_public:
            public_channels.append(username)
            logging.info(f"   ✅ @{username}")
        await asyncio.sleep(0.3)
    
    logging.info(f"\n📊 === СТАТИСТИКА ПОИСКА ===")
    logging.info(f"   Найдено @username: {stats['found_usernames']}")
    logging.info(f"   Из них публичных: {len(public_channels)}")
    logging.info(f"   Пропущено (боты/приватные): {stats['skipped_bots'] + stats['skipped_private']}")
    logging.info(f"   Найдено invite links: {stats['found_invites']}")
    
    if not public_channels and not discovered_invites:
        logging.info("\n✅ Новых чатов не найдено")
        await client.disconnect()
        return
    
    # === ЭТАП 2: ВСТУПЛЕНИЕ ===
    total_to_join = len(public_channels) + len(discovered_invites)
    logging.info(f"\n🤝 === НАЧИНАЮ ВСТУПЛЕНИЕ В {total_to_join} ЧАТОВ ===\n")
    
    if public_channels:
        logging.info(f"📡 Публичные каналы ({len(public_channels)}):\n")
        
        for idx, username in enumerate(public_channels, 1):
            logging.info(f"[{idx}/{len(public_channels)}]")
            success, chat_id, chat_title = await join_channel(client, username)
            
            if success:
                await save_chat(chat_id, chat_title, is_member=True)
            
            if idx < len(public_channels):  # Не ждём после последнего
                delay = random.randint(60, 90)
                logging.info(f"⏳ {delay} сек...\n")
                await asyncio.sleep(delay)
    
    if discovered_invites:
        logging.info(f"\n🔗 Invite links ({len(discovered_invites)}):\n")
        
        for idx, (invite_hash, meta) in enumerate(discovered_invites.items(), 1):
            logging.info(f"[{idx}/{len(discovered_invites)}]")
            success, chat_id, chat_title = await join_by_invite_link(client, invite_hash, meta)
            
            if success:
                await save_chat(chat_id, chat_title, is_member=True)
            
            if idx < len(discovered_invites):
                delay = random.randint(60, 90)
                logging.info(f"⏳ {delay} сек...\n")
                await asyncio.sleep(delay)
    
    # === ФИНАЛЬНАЯ СТАТИСТИКА ===
    total_joined = stats["joined_channels"] + stats["joined_invites"]
    
    logging.info("\n" + "="*50)
    logging.info("📊 === ФИНАЛЬНАЯ СТАТИСТИКА ===")
    logging.info("="*50)
    logging.info(f"✅ Вступил в публичные каналы: {stats['joined_channels']}")
    logging.info(f"✅ Вступил через invite links: {stats['joined_invites']}")
    logging.info(f"🎯 ВСЕГО ВСТУПИЛ: {total_joined}")
    logging.info(f"❌ Ошибок/пропусков: {stats['errors']}")
    logging.info("="*50 + "\n")
    
    # === ПОВТОРНОЕ СКАНИРОВАНИЕ ===
    if total_joined > 0:
        await scan_new_chats(client)
    
    logging.info("\n🎉 === СКРИПТ ЗАВЕРШЁН ===")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
