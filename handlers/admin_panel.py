"""Админ-роутер: команды модерации, создания и очистки."""
import json
from datetime import date
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy import delete, select, func, case

from config import config
from data.statuses import EventStatus
from database.models import ScrapedEvent
from dialogs.admin import admin_dialog
from dialogs.admin_review import review_dialog, create_dialog
from services.dedup import exact_dedup, fuzzy_dedup
from states import AdminCreateSG, AdminReviewSG, AdminSG
from database.session import AsyncSessionMaker


admin_router = Router()
admin_router.message.filter(lambda m: m.from_user and m.from_user.id == config.admin_id)

# Диалоги
admin_router.include_router(admin_dialog)
admin_router.include_router(review_dialog)
admin_router.include_router(create_dialog)


# ---------------------------------------------------------------------------
# Главные команды
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Очистка / дедупликация
# ---------------------------------------------------------------------------
@admin_router.message(Command("clean"))
async def cmd_clean_old(message: Message):
    """Удалить устаревшие события из review"""
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            delete(ScrapedEvent)
            .where(ScrapedEvent.status == EventStatus.REVIEW)
            .where(ScrapedEvent.event_date < date.today())
        )
        await session.commit()
        await message.answer(
            f"🗑 Удалено {result.rowcount} устаревших событий из review"
        )


@admin_router.message(Command("dedup"))
async def cmd_dedup_exact(message: Message):
    """Удалить точные дубликаты (pending + review)."""
    removed = await exact_dedup()
    await message.answer(f"🧹 Удалено точных дубликатов: {removed}")


@admin_router.message(Command("dedup_fuzzy"))
async def cmd_dedup_fuzzy(message: Message):
    """Удалить похожие события (≥80% по первым 200 символам)."""
    removed = await fuzzy_dedup()
    await message.answer(f"🧹 Удалено нечётких дубликатов: {removed}")


# ---------------------------------------------------------------------------
# Обсуждения мест
# ---------------------------------------------------------------------------
@admin_router.message(Command("addmention"))
async def cmd_add_mention(message: Message):
    """Добавить обсуждение к месту: /addmention <место> <ссылка>"""
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Формат: /addmention <название места> <ссылка на сообщение>\n\n"
            "Пример:\n/addmention Dreamland https://t.me/balichat/123456"
        )
        return

    place_name = args[1].lower()
    link = args[2].strip()

    if not link.startswith("https://t.me/"):
        await message.answer("❌ Ссылка должна быть на Telegram сообщение")
        return

    knowledge_dir = Path("knowledge_base")
    for json_file in knowledge_dir.glob("*.json"):
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

                with open(json_file, "w") as f:
                    json.dump(places, f, ensure_ascii=False, indent=2)

                await message.answer(
                    f"✅ Добавлено к <b>{place['name']}</b>\n"
                    f"Всего ссылок: {len(place['mentions'])}",
                    parse_mode="HTML",
                )
                return

    await message.answer(f"❌ Место '{place_name}' не найдено")


# ---------------------------------------------------------------------------
# Статистика и справка
# ---------------------------------------------------------------------------
@admin_router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика базы — один запрос с conditional aggregation."""
    async with AsyncSessionMaker() as session:
        row = await session.execute(
            select(
                func.count(ScrapedEvent.id).label("total"),
                func.sum(case((ScrapedEvent.status == EventStatus.PENDING, 1), else_=0)).label("pending"),
                func.sum(case((ScrapedEvent.status == EventStatus.REVIEW, 1), else_=0)).label("review"),
                func.sum(case((ScrapedEvent.status == EventStatus.APPROVED, 1), else_=0)).label("approved"),
                func.sum(case((ScrapedEvent.status == EventStatus.REJECTED, 1), else_=0)).label("rejected"),
            )
        )
        s = row.one()

    await message.answer(
        "📊 <b>Статистика базы:</b>\n"
        f"Всего событий: {s.total}\n"
        f"⏳ Pending: {s.pending}\n"
        f"👀 На модерации: {s.review}\n"
        f"✅ Опубликовано: {s.approved}\n"
        f"🗑 Отклонено: {s.rejected}",
        parse_mode="HTML",
    )


@admin_router.message(Command("reload_kb"))
async def cmd_reload_kb(message: Message):
    """Принудительно сбросить TTL-кэш базы знаний."""
    from services.ai_assistant import _get_knowledge
    from services.reviews_analyzer import _get_place_names
    import services.ai_assistant as _ai_mod
    import services.reviews_analyzer as _rev_mod

    # Сбрасываем TTL — следующий вызов перечитает с диска
    _ai_mod._knowledge_loaded_at = 0.0
    _rev_mod._place_names_loaded_at = 0.0

    # Прогреваем кэш сразу
    kb = _get_knowledge()
    pn = _get_place_names()
    await message.answer(
        f"♻️ База знаний перезагружена:\n"
        f"• {len(kb)} категорий мест\n"
        f"• {len(pn)} названий для review-анализа"
    )


@admin_router.message(Command("help"))
async def cmd_help(message: Message):
    """Список всех админ-команд"""
    await message.answer(
        "<b>📋 Админ-команды:</b>\n\n"
        "<b>Управление:</b>\n"
        "/admin — панель управления афишей\n"
        "/review — модерация новых событий\n"
        "/add — создать событие вручную\n\n"
        "<b>Очистка:</b>\n"
        "/clean — удалить устаревшие из review\n"
        "/dedup — удалить точные дубликаты\n"
        "/dedup_fuzzy — удалить похожие (≥80%)\n\n"
        "<b>Места:</b>\n"
        "/addmention &lt;место&gt; &lt;ссылка&gt; — добавить обсуждение\n\n"
        "<b>Сервис:</b>\n"
        "/stats — статистика бота\n"
        "/reload_kb — перезагрузить базу знаний\n"
        "/help — эта справка",
        parse_mode="HTML",
    )
