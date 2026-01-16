import asyncio
import logging
from database.models import AsyncSessionMaker, ScrapedEvent, init_db, compute_text_hash
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)

async def migrate():
    await init_db()
    
    async with AsyncSessionMaker() as session:
        result = await session.execute(select(ScrapedEvent).where(ScrapedEvent.text_hash == None))
        events = result.scalars().all()
        
        logging.info(f"Обновляю {len(events)} записей...")
        
        for event in events:
            event.text_hash = compute_text_hash(event.raw_text)
        
        await session.commit()
        logging.info("✅ Миграция OK")

if __name__ == "__main__":
    asyncio.run(migrate())
