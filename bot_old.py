import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.models import init_db, AsyncSessionMaker, ScrapedEvent
from services.analyzer import run_batch_analysis
from sqlalchemy import select, desc

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я Афиша Бали.\n"
        "Жми /feed чтобы посмотреть свежие ивенты."
    )

@dp.message(Command("digest"))
async def cmd_manual_digest(message: types.Message):
    """Ручной запуск анализа"""
    status_msg = await message.answer("🧠 Запускаю анализ...")
    result = await run_batch_analysis()
    await status_msg.edit_text(result)

@dp.message(Command("feed"))
async def cmd_feed(message: types.Message):
    """Показ ленты событий (до 30 штук)"""
    async with AsyncSessionMaker() as session:
        # Запрашиваем 50 последних, чтобы после фильтрации дублей осталось ~30
        query = select(ScrapedEvent).where(
            ScrapedEvent.status == "processed",
            ScrapedEvent.category != "Spam"
        ).order_by(desc(ScrapedEvent.created_at)).limit(50)
        
        result = await session.execute(query)
        events = result.scalars().all()
        
        if not events:
            await message.answer("📭 Лента пуста.")
            return

        text = "🌴 **Свежие анонсы (AI Digest):**\n\n"
        
        # Фильтр дубликатов по саммари
        seen_summaries = set()
        count = 0
        
        for e in events:
            # Если мы уже видели такое описание - пропускаем
            # (берем первые 50 символов для грубого сравнения)
            summary_snippet = (e.summary or "")[:50].lower()
            if summary_snippet in seen_summaries:
                continue
            seen_summaries.add(summary_snippet)
            
            icon = "▫️"
            if e.category == 'Free': icon = "🆓"
            elif e.category == 'Paid': icon = "💰"
            elif e.category == 'Networking': icon = "🤝"
            elif e.category == 'Contest': icon = "🎁"
            elif e.category == 'Party': icon = "🎉"
            
            # Формируем строку
            row = f"{icon} <b>{e.category}</b>\n{e.summary}\n👉 <a href='{e.link}'>Источник</a>\n\n"
            
            # Если сообщение слишком длинное, разбиваем
            if len(text) + len(row) > 4000:
                await message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                text = ""
            
            text += row
            count += 1
            if count >= 30: break # Лимит выдачи
            
        if text:
            await message.answer(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# --- ФОНОВЫЕ ЗАДАЧИ ---

async def scheduled_analysis():
    print("⏰ Планировщик: Запуск анализа...")
    await run_batch_analysis()

# --- ЗАПУСК ---

async def main():
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_analysis, 'interval', minutes=60)
    scheduler.start()
    
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
