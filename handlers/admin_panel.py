from aiogram import Router
from database.models import AsyncSessionMaker, ScrapedEvent
from sqlalchemy import delete
from datetime import date
import json
from pathlib import Path
from database.models import AsyncSessionMaker, ScrapedEvent
from sqlalchemy import delete
from datetime import date
import json
from pathlib import Path
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from config import config
from dialogs.admin import admin_dialog
from dialogs.admin_review import review_dialog, create_dialog
from states import AdminCreateSG, AdminReviewSG, AdminSG

admin_router = Router()
admin_router.message.filter(lambda m: m.from_user and m.from_user.id == config.admin_id)

# Подключаем диалоги
admin_router.include_router(admin_dialog)
admin_router.include_router(review_dialog)
admin_router.include_router(create_dialog)

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, dialog_manager: DialogManager):
    """Список всех событий для редактирования"""
    await dialog_manager.start(AdminSG.list, mode=StartMode.RESET_STACK)

@admin_router.message(Command("edit"))
async def cmd_edit(message: Message, dialog_manager: DialogManager):
    """Редактирование событий в ленте"""
    await dialog_manager.start(AdminSG.list, mode=StartMode.RESET_STACK)

@admin_router.message(Command("review"))
async def cmd_review(message: Message, dialog_manager: DialogManager):
    """Модерация новых событий"""
    await dialog_manager.start(AdminReviewSG.view, mode=StartMode.RESET_STACK)

@admin_router.message(Command("add"))
async def cmd_add(message: Message, dialog_manager: DialogManager):
    """Добавить событие вручную"""
    await dialog_manager.start(AdminCreateSG.summary, mode=StartMode.RESET_STACK)

@admin_router.message(Command("clean"))
async def cmd_clean_old(message: Message):
    """Удалить устаревшие события из review"""
    from sqlalchemy import delete
    from datetime import date
    
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            delete(ScrapedEvent)
            .where(ScrapedEvent.status == "review")
            .where(ScrapedEvent.event_date < date.today())
        )
        await session.commit()
        await message.answer(f"🗑 Удалено {result.rowcount} устаревших событий из review")

@admin_router.message(Command("addmention"))
async def cmd_add_mention(message: Message):
    """Добавить обсуждение к месту: /addmention <место> <ссылка>"""
    import json
    from pathlib import Path
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Формат: /addmention <название места> <ссылка на сообщение>\n\nПример:\n/addmention Dreamland https://t.me/balichat/123456")
        return
    
    place_name = args[1].lower()
    link = args[2].strip()
    
    if not link.startswith("https://t.me/"):
        await message.answer("❌ Ссылка должна быть на Telegram сообщение")
        return
    
    # Ищем место в базе знаний
    KNOWLEDGE_DIR = Path("knowledge_base")
    found = False
    
    for json_file in KNOWLEDGE_DIR.glob("*.json"):
        with open(json_file) as f:
            places = json.load(f)
        
        for place in places:
            if place_name in place.get("name", "").lower():
                mentions = place.get("mentions", [])
                
                # Проверяем дубль
                if any(m["link"] == link for m in mentions):
                    await message.answer(f"⚠️ Эта ссылка уже добавлена к {place['name']}")
                    return
                
                mentions.append({"link": link, "chat": "manual"})
                place["mentions"] = mentions[:5]  # Макс 5
                found = True
                
                with open(json_file, 'w') as f:
                    json.dump(places, f, ensure_ascii=False, indent=2)
                
                await message.answer(f"✅ Добавлено обсуждение к <b>{place['name']}</b>\n\nВсего ссылок: {len(place['mentions'])}", parse_mode="HTML")
                return
    
    if not found:
        await message.answer(f"❌ Место '{place_name}' не найдено в базе")

@admin_router.message(Command("clean"))
async def cmd_clean_old(message: Message):
    """Удалить устаревшие события из review"""
    from sqlalchemy import delete
    from datetime import date
    from database.models import AsyncSessionMaker, ScrapedEvent
    
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            delete(ScrapedEvent)
            .where(ScrapedEvent.status == "review")
            .where(ScrapedEvent.event_date < date.today())
        )
        await session.commit()
        await message.answer(f"🗑 Удалено {result.rowcount} устаревших событий из review")


@admin_router.message(Command("addmention"))
async def cmd_add_mention(message: Message):
    """Добавить обсуждение к месту: /addmention <место> <ссылка>"""
    import json
    from pathlib import Path
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Формат: /addmention <название места> <ссылка>\n\n"
            "Пример:\n/addmention Dreamland https://t.me/balichat/123456"
        )
        return
    
    place_name = args[1].lower()
    link = args[2].strip()
    
    if not link.startswith("https://t.me/"):
        await message.answer("❌ Ссылка должна быть на Telegram сообщение")
        return
    
    KNOWLEDGE_DIR = Path("knowledge_base")
    
    for json_file in KNOWLEDGE_DIR.glob("*.json"):
        with open(json_file) as f:
            places = json.load(f)
        
        for place in places:
            if place_name in place.get("name", "").lower():
                mentions = place.get("mentions", [])
                
                if any(m["link"] == link for m in mentions):
                    await message.answer(f"⚠️ Ссылка уже есть у {place['name']}")
                    return
                
                mentions.append({"link": link, "chat": "manual"})
                place["mentions"] = mentions[:5]
                
                with open(json_file, 'w') as f:
                    json.dump(places, f, ensure_ascii=False, indent=2)
                
                await message.answer(
                    f"✅ Добавлено к <b>{place['name']}</b>\nВсего ссылок: {len(place['mentions'])}",
                    parse_mode="HTML"
                )
                return
    
    await message.answer(f"❌ Место '{place_name}' не найдено")


@admin_router.message(Command("dedup"))
async def cmd_dedup_review(message: Message):
    """Удалить дубликаты из review (только полное совпадение текста)"""
    from sqlalchemy import select, func
    from database.models import AsyncSessionMaker, ScrapedEvent
    
    async with AsyncSessionMaker() as session:
        # Находим дубликаты по raw_text в review
        subq = (
            select(ScrapedEvent.raw_text)
            .where(ScrapedEvent.status == "review")
            .where(ScrapedEvent.raw_text.isnot(None))
            .group_by(ScrapedEvent.raw_text)
            .having(func.count() > 1)
        ).subquery()
        
        # Получаем все дубликаты
        result = await session.execute(
            select(ScrapedEvent)
            .where(ScrapedEvent.status == "review")
            .where(ScrapedEvent.raw_text.in_(select(subq.c.raw_text)))
            .order_by(ScrapedEvent.raw_text, ScrapedEvent.created_at.desc())
        )
        
        events = result.scalars().all()
        
        # Группируем и оставляем только первый (самый новый)
        seen_texts = set()
        to_delete = []
        
        for event in events:
            if event.raw_text in seen_texts:
                to_delete.append(event.id)
            else:
                seen_texts.add(event.raw_text)
        
        # Удаляем дубликаты
        if to_delete:
            from sqlalchemy import delete
            await session.execute(
                delete(ScrapedEvent).where(ScrapedEvent.id.in_(to_delete))
            )
            await session.commit()
        
        await message.answer(f"🗑 Удалено {len(to_delete)} дубликатов из review")


@admin_router.message(Command("help"))
async def cmd_help(message: Message):
    """Список всех админ-команд"""
    await message.answer(
        "<b>📋 Админ-команды:</b>\n\n"
        "<b>Управление:</b>\n"
        "/admin — панель управления афишей\n"
        "/review — модерация новых событий\n"
        "/create — создать событие вручную\n\n"
        "<b>Очистка:</b>\n"
        "/clean — удалить устаревшие из review\n"
        "/dedup — удалить дубликаты (100%)\n"
        "/dedup_fuzzy — удалить похожие (≥40%)\n\n"
        "<b>Места:</b>\n"
        "/addmention &lt;место&gt; &lt;ссылка&gt; — добавить обсуждение\n\n"
        "<b>Сервис:</b>\n"
        "/stats — статистика бота\n"
        "/help — эта справка",
        parse_mode="HTML"
    )

