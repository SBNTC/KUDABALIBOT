from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import ScrapedEvent
from config import config

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    if message.from_user.id != config.admin_id:
        return

    total = await session.scalar(select(func.count(ScrapedEvent.id)))
    pending = await session.scalar(select(func.count(ScrapedEvent.id)).where(ScrapedEvent.status == "pending"))
    approved = await session.scalar(select(func.count(ScrapedEvent.id)).where(ScrapedEvent.status == "approved"))
    spam = await session.scalar(select(func.count(ScrapedEvent.id)).where(ScrapedEvent.category == "Spam"))

    text = (
        f"📊 <b>Статистика базы:</b>\n"
        f"Всего событий: {total}\n"
        f"⏳ Ожидают AI: {pending}\n"
        f"✅ Опубликовано: {approved}\n"
        f"🗑 Спам: {spam}"
    )
    await message.answer(text, parse_mode="HTML")
