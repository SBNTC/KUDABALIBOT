import operator
from datetime import date
from typing import Optional

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Calendar, Cancel, Column, Row, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, Jinja

from data.categories import EventCategory, CATEGORY_ICONS
from database.models import AsyncSessionMaker, ScrapedEvent
from database.requests import (
    create_manual_event,
    update_event_category,
    update_event_date,
    update_event_status,
    update_event_summary,
)
from sqlalchemy import select

from states import AdminCreateSG, AdminReviewSG


# ---------- GETTERS ----------

async def get_next_review_event(dialog_manager: DialogManager, **kwargs):
    async with AsyncSessionMaker() as session:
        ev: Optional[ScrapedEvent] = await session.scalar(
            select(ScrapedEvent)
            .where(ScrapedEvent.status == "review")
            .order_by(ScrapedEvent.created_at.asc())
            .limit(1)
        )

        if not ev:
            dialog_manager.dialog_data["event_id"] = None
            return {"has_event": False}

        dialog_manager.dialog_data["event_id"] = int(ev.id)

        icon = CATEGORY_ICONS.get(ev.category, "❓")
        return {
            "has_event": True,
            "id": ev.id,
            "category": ev.category,
            "cat_icon": icon,
            "date": ev.event_date.isoformat() if ev.event_date else "Не указана",
            "link": ev.link or "",
            "summary": ev.summary or "-",
            "raw": (ev.raw_text or "")[:1200],
        }


def _require_event_id(manager: DialogManager) -> int:
    event_id = manager.dialog_data.get("event_id")
    if not event_id:
        raise RuntimeError("event_id is missing in dialog_data")
    return int(event_id)


# ---------- ACTIONS (3 кнопки) ----------

async def on_approve(c: CallbackQuery, button: Button, manager: DialogManager):
    event_id = _require_event_id(manager)
    async with AsyncSessionMaker() as session:
        await update_event_status(session, event_id, "approved")
    await c.answer("✅ Подтверждено")
    await manager.switch_to(AdminReviewSG.view)


async def on_reject(c: CallbackQuery, button: Button, manager: DialogManager):
    event_id = _require_event_id(manager)
    async with AsyncSessionMaker() as session:
        await update_event_status(session, event_id, "rejected")
    await c.answer("❌ Отклонено")
    await manager.switch_to(AdminReviewSG.view)


# ---------- EDIT ACTIONS ----------

async def on_summary_input(message: Message, widget: MessageInput, manager: DialogManager):
    event_id = _require_event_id(manager)
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустой текст не сохранён.")
        return
    async with AsyncSessionMaker() as session:
        await update_event_summary(session, event_id, text)
    await message.answer("✅ Текст обновлён")
    await manager.switch_to(AdminReviewSG.view)



async def on_clear_date_review(c: CallbackQuery, button, manager: DialogManager):
    """Убрать дату"""
    event_id = manager.dialog_data.get("event_id")
    async with AsyncSessionMaker() as session:
        await update_event_date(session, event_id, None)
    await c.answer("✅ Дата убрана")
    await manager.switch_to(AdminReviewSG.view)

async def on_clear_date_review(c: CallbackQuery, button, manager: DialogManager):
    """Убрать дату в review"""
    event_id = _require_event_id(manager)
    async with AsyncSessionMaker() as session:
        await update_event_date(session, event_id, None)
    await c.answer("✅ Дата убрана")
    await manager.switch_to(AdminReviewSG.view)


async def on_date_selected(c: CallbackQuery, widget: Calendar, manager: DialogManager, selected_date: date):
    event_id = _require_event_id(manager)
    async with AsyncSessionMaker() as session:
        await update_event_date(session, event_id, selected_date)
    await c.answer(f"✅ Дата: {selected_date}")
    await manager.switch_to(AdminReviewSG.view)


async def on_category_selected(c: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    event_id = _require_event_id(manager)
    async with AsyncSessionMaker() as session:
        await update_event_category(session, event_id, item_id)
    await c.answer(f"✅ Категория: {item_id}")
    await manager.switch_to(AdminReviewSG.view)


async def get_categories(**kwargs):
    return {
        "cats": [(f"{CATEGORY_ICONS.get(c.value, '')} {c.value}", c.value) for c in EventCategory]
    }


# ---------- CREATE MANUAL EVENT ACTIONS (/add) ----------

async def on_create_summary(message: Message, widget: MessageInput, manager: DialogManager):
    txt = (message.text or "").strip()
    if not txt:
        await message.answer("Пустой текст не сохранён.")
        return
    manager.dialog_data["new_summary"] = txt
    manager.dialog_data["new_date"] = None
    manager.dialog_data["new_category"] = None
    await manager.switch_to(AdminCreateSG.date)


async def on_create_date_selected(c: CallbackQuery, widget: Calendar, manager: DialogManager, selected_date: date):
    manager.dialog_data["new_date"] = selected_date
    await c.answer(f"✅ Дата: {selected_date}")
    await manager.switch_to(AdminCreateSG.category)


async def on_create_skip_date(c: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data["new_date"] = None
    await c.answer("✅ Без даты")
    await manager.switch_to(AdminCreateSG.category)


async def on_create_category_selected(c: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    manager.dialog_data["new_category"] = item_id

    summary = manager.dialog_data.get("new_summary")
    new_date = manager.dialog_data.get("new_date")
    category = manager.dialog_data.get("new_category")

    async with AsyncSessionMaker() as session:
        new_id = await create_manual_event(
            session=session,
            summary=summary,
            category=category,
            event_date=new_date,
        )

    await c.answer(f"✅ Добавлено (ID: {new_id})")
    await manager.done()
    
    # Отправляем подтверждение в чат, чтобы админ видел результат
    await c.message.answer(
        f"🎉 <b>Событие успешно добавлено!</b>\n"
        f"🆔 ID: {new_id}\n"
        f"📂 {category}\n"
        f"📝 {summary[:100]}...",
        parse_mode="HTML"
    )


# ---------- DIALOG 1: REVIEW ----------

review_dialog = Dialog(
    Window(
        Jinja(
            "{% if has_event %}"
            "🚦 <b>Очередь модерации</b>\n\n"
            "🆔 <b>ID:</b> {{id}}\n"
            "📂 <b>Категория:</b> {{cat_icon}} {{category}}\n"
            "📅 <b>Дата:</b> {{date}}\n"
            "🔗 <a href='{{link}}'>Источник</a>\n\n"
            "📝 <b>Текст:</b>\n{{summary}}\n\n"
            "📄 <b>Raw:</b>\n<tg-spoiler>{{raw}}</tg-spoiler>\n"
            "{% else %}"
            "✅ Очередь пуста\n"
            "{% endif %}"
        ),
        Row(
            Button(Const("✅ Подтвердить"), id="approve", on_click=on_approve, when="has_event"),
            Button(Const("❌ Отклонить"), id="reject", on_click=on_reject, when="has_event"),
        ),
        Row(
            SwitchTo(Const("✏️ Редактировать"), id="to_edit", state=AdminReviewSG.edit_menu, when="has_event"),
        ),
        Button(Const("🔄 Обновить"), id="refresh", on_click=lambda c, b, m: m.switch_to(AdminReviewSG.view)),
        Cancel(Const("✖ Закрыть")),
        state=AdminReviewSG.view,
        getter=get_next_review_event,
        parse_mode="HTML",
    ),

    Window(
        Const("✏️ Редактирование:\nВыбери, что менять."),
        Column(
            SwitchTo(Const("📝 Изменить текст"), id="ed_sum", state=AdminReviewSG.edit_summary),
            SwitchTo(Const("📅 Изменить дату"), id="ed_date", state=AdminReviewSG.edit_date),
            SwitchTo(Const("📂 Изменить категорию"), id="ed_cat", state=AdminReviewSG.edit_category),
            SwitchTo(Const("🔙 Назад"), id="back1", state=AdminReviewSG.view),
        ),
        state=AdminReviewSG.edit_menu,
    ),

    Window(
        Const("📝 Отправь новый текст одним сообщением:"),
        MessageInput(on_summary_input),
        SwitchTo(Const("🔙 Назад"), id="back2", state=AdminReviewSG.view),
        state=AdminReviewSG.edit_summary,
    ),

    Window(
        Const("📅 Выбери дату:"),
        Calendar(id="cal_edit", on_click=on_date_selected),
        Button(Const("🚫 Без даты"), id="no_date_review", on_click=on_clear_date_review),
        SwitchTo(Const("🔙 Назад"), id="back3", state=AdminReviewSG.view),
        state=AdminReviewSG.edit_date,
    ),

    Window(
        Const("📂 Выбери категорию:"),
        Select(
            Format("{item[0]}"),
            id="cat_edit",
            items="cats",
            item_id_getter=operator.itemgetter(1),
            on_click=on_category_selected,
        ),
        SwitchTo(Const("🔙 Назад"), id="back4", state=AdminReviewSG.view),
        state=AdminReviewSG.edit_category,
        getter=get_categories,
    ),
)

# ---------- DIALOG 2: CREATE ----------

create_dialog = Dialog(
    Window(
        Const("➕ Добавление события вручную\n\nОтправь текст (что увидит пользователь) одним сообщением:"),
        MessageInput(on_create_summary),
        Cancel(Const("✖ Отмена")),
        state=AdminCreateSG.summary,
    ),

    Window(
        Const("📅 Выбери дату события (или пропусти):"),
        Calendar(id="cal_new", on_click=on_create_date_selected),
        Button(Const("⏭ Без даты"), id="skip_date", on_click=on_create_skip_date),
        Cancel(Const("✖ Отмена")),
        state=AdminCreateSG.date,
    ),

    Window(
        Const("📂 Выбери категорию:"),
        Select(
            Format("{item[0]}"),
            id="cat_new",
            items="cats",
            item_id_getter=operator.itemgetter(1),
            on_click=on_create_category_selected,
        ),
        Cancel(Const("✖ Отмена")),
        state=AdminCreateSG.category,
        getter=get_categories,
    ),
)
