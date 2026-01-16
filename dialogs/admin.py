import operator
from datetime import date
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Format, Const, Jinja
from aiogram_dialog.widgets.kbd import (
    ScrollingGroup, Select, Button, SwitchTo, Back, Cancel, Column, Row, Radio, Calendar
)
from aiogram_dialog.widgets.input import MessageInput
from database.requests import (
    get_all_events, get_event_by_id, delete_event_by_id, 
    update_event_category, update_event_date, update_event_summary
)
from database.models import AsyncSessionMaker
from data.categories import EventCategory, CATEGORY_ICONS
from states import AdminSG

# --- Handlers ---

async def on_search_input(message: Message, widget, manager: DialogManager):
    manager.dialog_data["search_query"] = message.text

async def on_clear_search(c: CallbackQuery, widget, manager: DialogManager):
    manager.dialog_data["search_query"] = None

async def on_category_filter_changed(c: CallbackQuery, widget, manager: DialogManager, item_id: str):
    if manager.dialog_data.get("cat_filter") == item_id:
        manager.dialog_data["cat_filter"] = None
    else:
        manager.dialog_data["cat_filter"] = item_id

async def on_event_selected(c: CallbackQuery, widget, manager: DialogManager, item_id: str):
    manager.dialog_data["event_id"] = item_id
    await manager.switch_to(AdminSG.view)

async def on_delete_click(c: CallbackQuery, widget, manager: DialogManager):
    event_id = int(manager.dialog_data["event_id"])
    async with AsyncSessionMaker() as session:
        await delete_event_by_id(session, event_id)
    await c.answer("✅ Удалено")
    await manager.switch_to(AdminSG.list)

async def on_category_changed(c: CallbackQuery, widget, manager: DialogManager, item_id: str):
    event_id = int(manager.dialog_data["event_id"])
    async with AsyncSessionMaker() as session:
        await update_event_category(session, event_id, item_id)
    await c.answer(f"✅ Категория: {item_id}")
    await manager.switch_to(AdminSG.view)

async def on_clear_date(c: CallbackQuery, button, manager: DialogManager):
    """Убрать дату (регулярное событие)"""
    event_id = manager.dialog_data.get("event_id")
    async with AsyncSessionMaker() as session:
        await update_event_date(session, event_id, None)
    await c.answer("✅ Дата убрана")
    await manager.switch_to(AdminSG.view)


async def on_date_selected(c: CallbackQuery, widget, manager: DialogManager, selected_date: date):
    event_id = int(manager.dialog_data["event_id"])
    async with AsyncSessionMaker() as session:
        await update_event_date(session, event_id, selected_date)
    await c.answer(f"✅ Дата: {selected_date}")
    await manager.switch_to(AdminSG.view)

async def on_summary_input(message: Message, widget, manager: DialogManager):
    """Обработчик ввода нового текста описания"""
    event_id = int(manager.dialog_data["event_id"])
    new_text = message.text
    async with AsyncSessionMaker() as session:
        await update_event_summary(session, event_id, new_text)
    await message.answer("✅ Описание обновлено!")
    await manager.switch_to(AdminSG.view)

# --- Getters ---

async def get_events_list(dialog_manager: DialogManager, **kwargs):
    search = dialog_manager.dialog_data.get("search_query")
    cat_filter = dialog_manager.dialog_data.get("cat_filter")
    
    async with AsyncSessionMaker() as session:
        events = await get_all_events(session, search_query=search, category_filter=cat_filter)
        items = []
        for e in events:
            icon = CATEGORY_ICONS.get(e.category, "❓")
            title_text = e.chat_title or "No Title"
            date_str = f"[{e.event_date.strftime('%d.%m')}] " if e.event_date else ""
            items.append({
                "id": e.id,
                "title_str": f"{icon} {date_str}{title_text[:10]}... | {e.summary[:15] if e.summary else '...'}"
            })
            
        return {
            "events": items,
            "search_status": f"🔍 Поиск: {search}" if search else "⌨️ Отправь текст для поиска",
            "is_searching": bool(search),
            "count": len(events)
        }

async def get_filter_categories(**kwargs):
    cats = [(f"{cat.value}", cat.value) for cat in EventCategory]
    return {"filter_cats": cats}

async def get_event_details(dialog_manager: DialogManager, **kwargs):
    event_id = dialog_manager.dialog_data.get("event_id")
    async with AsyncSessionMaker() as session:
        event = await get_event_by_id(session, int(event_id))
        if not event:
            return {"text": "❌ Ошибка: событие не найдено"}
            
        return {
            "id": event.id,
            "category": event.category,
            "icon": CATEGORY_ICONS.get(event.category, "❓"),
            "summary": event.summary if event.summary else "-",
            "link": event.link,
            "date": event.event_date if event.event_date else "Не указана",
            "raw": event.raw_text[:200] + "..." if event.raw_text else ""
        }

async def get_edit_categories(**kwargs):
    return {
        "categories": [(f"{CATEGORY_ICONS.get(c, '')} {c.value}", c.value) for c in EventCategory]
    }

# --- Dialog Structure ---

admin_dialog = Dialog(
    # 1. СПИСОК
    Window(
        Format("🔧 <b>Админка</b> [Найдено: {count}]\n"),
        Format("{search_status}"),
        ScrollingGroup(
            Radio(Format("🔘 {item[0]}"), Format("✅ {item[0]}"), id="r_filter", item_id_getter=operator.itemgetter(1), items="filter_cats", on_click=on_category_filter_changed),
            id="scroll_cats", width=3, height=1, hide_on_single_page=True
        ),
        Row(Button(Const("❌ Сброс поиска"), id="btn_clear", on_click=on_clear_search, when="is_searching")),
        ScrollingGroup(
            Select(Format("{item[title_str]}"), id="s_events", item_id_getter=operator.itemgetter("id"), items="events", on_click=on_event_selected),
            id="scroller", width=1, height=6, hide_on_single_page=True,
        ),
        Cancel(Const("🚪 Выход")),
        MessageInput(on_search_input),
        state=AdminSG.list,
        getter=[get_events_list, get_filter_categories],
    ),
    
    # 2. ПРОСМОТР
    Window(
        Jinja(
            "🆔 <b>ID:</b> {{id}}\n"
            "📂 <b>Категория:</b> {{icon}} {{category}}\n"
            "📅 <b>Дата:</b> {{date}}\n"
            "🔗 <a href='{{link}}'>Источник</a>\n\n"
            "🤖 <b>AI Summary:</b>\n{{summary}}\n\n"
            "📄 <b>Raw Text:</b>\n<pre>{{raw}}</pre>"
        ),
        Column(
            SwitchTo(Const("📝 Редактировать текст"), id="to_sum", state=AdminSG.edit_summary), # Новая кнопка
            SwitchTo(Const("📅 Изменить дату"), id="to_date", state=AdminSG.edit_date),
            SwitchTo(Const("✏️ Сменить категорию"), id="to_cat", state=AdminSG.edit_category),
            Button(Const("🗑 УДАЛИТЬ"), id="btn_del", on_click=on_delete_click),
        ),
        Back(Const("🔙 Назад")),
        state=AdminSG.view,
        getter=get_event_details,
        parse_mode="HTML"
    ),

    # 3. КАТЕГОРИИ
    Window(
        Const("Выберите новую категорию:"),
        Column(
            Select(Format("{item[0]}"), id="s_cats_edit", item_id_getter=operator.itemgetter(1), items="categories", on_click=on_category_changed)
        ),
        Back(Const("🔙 Отмена")),
        state=AdminSG.edit_category,
        getter=get_edit_categories
    ),

    # 4. КАЛЕНДАРЬ
    Window(
        Const("📅 <b>Выберите дату события:</b>"),
        Calendar(id="cal", on_click=on_date_selected),
        Back(Const("🔙 Отмена")),
        state=AdminSG.edit_date
    ),

    # 5. РЕДАКТИРОВАНИЕ ТЕКСТА (Новое окно)
    Window(
        Const("📝 <b>Отправьте новый текст описания:</b>\n\nМожете скопировать старый текст и исправить его."),
        MessageInput(on_summary_input),
        Back(Const("🔙 Отмена")),
        state=AdminSG.edit_summary
    ),
)
