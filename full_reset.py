"""Полный сброс и первичный сбор"""
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

async def main():
    # 1. Удаляем старую БД
    if os.path.exists("events.db"):
        os.remove("events.db")
        logging.info("🗑 БД удалена")
    
    # 2. Создаём новую
    from database.models import init_db
    await init_db()
    logging.info("✅ БД создана")
    
    # 3. Сбор из чатов
    logging.info("📡 Сбор из Telegram чатов...")
    from services.collector import run_manual_scan
    await run_manual_scan()
    
    # 4. Сбор с сайта
    logging.info("🌐 Сбор с baliforum.ru...")
    from services.site_parser import run_site_parser
    await run_site_parser()
    
    # 5. Проверка
    from database.models import AsyncSessionMaker, ScrapedEvent
    from sqlalchemy import select, func
    async with AsyncSessionMaker() as session:
        total = await session.scalar(select(func.count(ScrapedEvent.id)))
        logging.info(f"📊 Собрано: {total}")
    
    # 6. AI анализ
    logging.info("🧠 Запуск AI анализа...")
    from services.analyzer import run_batch_analysis
    while True:
        result = await run_batch_analysis()
        logging.info(f"📊 {result}")
        if "📭" in result or "Нет новых" in result:
            break
        await asyncio.sleep(2)
    
    # 7. Финальная статистика
    async with AsyncSessionMaker() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(ScrapedEvent.status, func.count(ScrapedEvent.id))
            .group_by(ScrapedEvent.status)
        )
        stats = result.all()
        logging.info("📊 Итого по статусам:")
        for status, count in stats:
            logging.info(f"   {status}: {count}")
    
    logging.info("✅ Готово! Запускай бота: screen -S bot -dm python bot.py")

if __name__ == "__main__":
    asyncio.run(main())
