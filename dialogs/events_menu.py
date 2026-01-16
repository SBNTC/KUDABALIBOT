from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row, ScrollingGroup, Select, Back
from aiogram_dialog.widgets.text import Const, Format
from sqlalchemy import select
from database.models import AsyncSessionMaker, ScrapedEvent # Используем models везде одинаково
from dialogs.states import EventsSG

async def get_events(dialog_manager: DialogManager, **kwargs):
    flt = dialog_manager.dialog_data.get("filter", "all")
    
    async with AsyncSessionMaker() as session:
        # ВАЖНО: status == "approved"
        query = select(ScrapedEvent).where(
            ScrapedEvent.status == "approved"
        ).order_by(ScrapedEvent.created_at.desc()).limit(50)
        
        if flt != "all":
            query = query.where(ScrapedEvent.category == flt)
            
        result = await session.execute(query)
        events = result.scalars().all()

    return {
        "events": events,
        "filter_name": "Бесплатные" if flt == "free" else "Платные" if flt == "paid" else "Все"
    }

async def set_filter(c, w, m, item_id):
    m.dialog_data["filter"] = item_id
    await m.switch_to(EventsSG.list)

async def on_event_click(c, w, m, item_id):
    async with AsyncSessionMaker() as s:
        ev = await s.get(ScrapedEvent, int(item_id))
        if ev:
            await c.message.answer(
                f"📅 <b>{ev.summary}</b>\n\n"
                f"{ev.raw_text[:300]}...\n\n"
                f"<a href='{ev.link}'>🔗 Ссылка</a>",
                parse_mode="HTML"
            )

# Окна
main_window = Window(
    Const("🔍 Что ищем?"),
    Row(
        Button(Const("🆓 Free"), id="f_free", on_click=lambda c,b,m: set_filter(c,b,m,"free")),
        Button(Const("💰 Paid"), id="f_paid", on_click=lambda c,b,m: set_filter(c,b,m,"paid")),
    ),
    Button(Const("🌐 Все подряд"), id="f_all", on_click=lambda c,b,m: set_filter(c,b,m,"all")),
    state=EventsSG.menu
)

list_window = Window(
    Format("Список: <b>{filter_name}</b>"),
    ScrollingGroup(
        Select(
            Format("{item.summary}"),
            id="sel",
            item_id_getter=lambda x: x.id,
            items="events",
            on_click=on_event_click
        ),
        id="scrl",
        width=1,
        height=6,
        hide_on_single_page=True
    ),
    Back(Const("🔙 Назад")),
    state=EventsSG.list,
    getter=get_events
)

events_menu_dialog = Dialog(main_window, list_window)
