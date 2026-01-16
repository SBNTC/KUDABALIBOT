from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy import select, desc
from config import config
from database.models import AsyncSessionMaker, ScrapedEvent
from services.analyzer import run_batch_analysis
from dialogs.states import AdminReviewSG

router = Router()
# Фильтр на админа
router.message.filter(F.from_user.id == config.admin_id)

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        "/ids - 📋 <b>Список ID (Последние 20)</b>\n"
        "/review - 🚦 Очередь модерации\n"
        "/edit ID - ✏️ Редактировать по ID\n"
        "/force_analyze - 🧠 Запуск AI",
        parse_mode="HTML"
    )

@router.message(Command("ids"))
async def cmd_list_ids(message: types.Message):
    """Простой список ID для копирования"""
    async with AsyncSessionMaker() as session:
        # Берем последние 20 опубликованных
        query = select(ScrapedEvent).where(
            ScrapedEvent.status == "approved"
        ).order_by(desc(ScrapedEvent.created_at)).limit(20)
        
        result = await session.execute(query)
        events = result.scalars().all()

    if not events:
        await message.answer("📭 Опубликованных событий нет.")
        return

    lines = ["📋 <b>ID последних событий:</b>\n"]
    for e in events:
        # Формат: ID (копируется) - Название
        lines.append(f"<code>{e.id}</code> — {e.summary}")
    
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(Command("review"))
async def start_review_mode(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(AdminReviewSG.view_queue, mode=StartMode.RESET_STACK)

@router.message(Command("edit"))
async def cmd_edit_event(message: types.Message, command: CommandObject, dialog_manager: DialogManager):
    if not command.args:
        await message.answer("⚠️ Пиши: <code>/edit 123</code>")
        return
    try:
        await dialog_manager.start(
            AdminReviewSG.view_queue, 
            mode=StartMode.RESET_STACK,
            data={"event_id": int(command.args)}
        )
    except ValueError:
        await message.answer("❌ ID должен быть числом")

@router.message(Command("force_analyze"))
async def cmd_force_analyze(message: types.Message):
    msg = await message.answer("🧠 Запускаю анализ...")
    result = await run_batch_analysis()
    await msg.edit_text(f"📊 {result}")
