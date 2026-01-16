import asyncio
import logging
from telethon import TelegramClient
from telethon.errors import MessageIdInvalidError, ChannelPrivateError
from sqlalchemy import select, delete
from database.models import AsyncSessionMaker, ScrapedEvent
from config import config


async def check_dead_links():
    """Проверка и удаление мёртвых ссылок"""
    logging.info("🔗 Проверка ссылок...")
    
    client = TelegramClient('anon_session', config.telegram_api_id, config.telegram_api_hash)
    await client.start()
    
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(ScrapedEvent).where(ScrapedEvent.status == "processed")
        )
        events = result.scalars().all()
        
        dead_count = 0
        
        for event in events:
            link = event.link
            
            # Пропускаем ссылки на сайты
            if "baliforum.ru" in link:
                continue
            
            try:
                # Парсим ссылку t.me/channel/123
                if "/c/" in link:
                    # Приватный канал: t.me/c/123456/789
                    parts = link.split("/")
                    channel_id = int("-100" + parts[-2])
                    msg_id = int(parts[-1])
                else:
                    # Публичный: t.me/channel/123
                    parts = link.replace("https://", "").split("/")
                    if len(parts) < 3:
                        continue
                    username = parts[1]
                    msg_id = int(parts[2])
                    channel_id = username
                
                # Проверяем существование
                try:
                    await client.get_messages(channel_id, ids=msg_id)
                except MessageIdInvalidError:
                    await session.execute(
                        delete(ScrapedEvent).where(ScrapedEvent.id == event.id)
                    )
                    dead_count += 1
                    logging.info(f"🗑 Удалено: #{event.id}")
                except ChannelPrivateError:
                    pass  # Канал закрыт, но ссылка может работать
                except Exception:
                    pass
                    
            except Exception as e:
                continue
            
            await asyncio.sleep(0.5)  # Задержка между проверками
        
        await session.commit()
    
    await client.disconnect()
    logging.info(f"✅ Проверка завершена. Удалено: {dead_count}")
    return dead_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(check_dead_links())
