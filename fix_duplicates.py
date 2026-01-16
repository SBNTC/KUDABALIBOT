"""Скрипт удаления дублей из БД"""
import asyncio
from sqlalchemy import select, delete
from database.models import AsyncSessionMaker, ScrapedEvent, init_db

async def remove_duplicates():
    await init_db()
    
    async with AsyncSessionMaker() as session:
        # Находим дубли по link
        query = select(ScrapedEvent.link, ScrapedEvent.id).order_by(
            ScrapedEvent.link, ScrapedEvent.created_at
        )
        result = await session.execute(query)
        all_events = result.all()
        
        seen_links = {}
        ids_to_delete = []
        
        for link, event_id in all_events:
            if link in seen_links:
                # Это дубль — удаляем
                ids_to_delete.append(event_id)
            else:
                seen_links[link] = event_id
        
        if ids_to_delete:
            await session.execute(
                delete(ScrapedEvent).where(ScrapedEvent.id.in_(ids_to_delete))
            )
            await session.commit()
            print(f"✅ Удалено дублей: {len(ids_to_delete)}")
        else:
            print("✅ Дублей не найдено")

asyncio.run(remove_duplicates())
