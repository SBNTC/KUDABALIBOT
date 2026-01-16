"""Статистика бота"""
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select, func

from database.models import AsyncSessionMaker, ScrapedEvent
from data.categories import EventCategory

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Показать статистику"""
    async with AsyncSessionMaker() as session:
        # Всего собрано
        total = await session.scalar(select(func.count(ScrapedEvent.id)))
        
        # Обработано
        processed = await session.scalar(
            select(func.count(ScrapedEvent.id))
            .where(ScrapedEvent.status == "processed")
        )
        
        # По категориям
        categories = {}
        for cat in EventCategory:
            count = await session.scalar(
                select(func.count(ScrapedEvent.id))
                .where(ScrapedEvent.category == cat.value)
            )
            if count > 0:
                categories[cat.value] = count
        
        text = "📊 <b>Статистика:</b>\n\n"
        text += f"📥 Собрано сообщений: {total}\n"
        text += f"✅ Обработано: {processed}\n\n"
        
        if categories:
            text += "<b>По категориям:</b>\n"
            for cat, count in categories.items():
                text += f"  • {cat}: {count}\n"
        
        await message.answer(text)
