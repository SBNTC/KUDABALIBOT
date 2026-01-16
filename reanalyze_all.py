"""Переанализировать все события"""
import asyncio
from sqlalchemy import update
from database.models import AsyncSessionMaker, ScrapedEvent, init_db

async def reset_status():
    await init_db()
    
    async with AsyncSessionMaker() as session:
        # Сбрасываем статус на pending (кроме спама)
        await session.execute(
            update(ScrapedEvent)
            .where(ScrapedEvent.category != "Spam")
            .values(status="pending", category=None, summary=None)
        )
        await session.commit()
        print("✅ Статус сброшен. Запусти /digest в боте для повторного анализа")

asyncio.run(reset_status())
