from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from filters import IsAdmin
from services.analyzer import run_batch_analysis

router = Router()


@router.message(Command("digest"), IsAdmin())
async def cmd_digest(message: Message):
    status_msg = await message.answer("🧠 Запускаю AI анализ...")
    result_text = await run_batch_analysis()
    await status_msg.edit_text(result_text)
