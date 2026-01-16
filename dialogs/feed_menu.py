import os
import math
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Column, StubScroll, NumberedPager, Select
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.input import MessageInput
from sqlalchemy import select, func, or_
from datetime import date

from database.models import AsyncSessionMaker, ScrapedEvent, User, UserAction, compute_text_hash
from data.categories import CATEGORY_ICONS
from states import FeedMenuStates
from services.ai_assistant import get_ai_response

EVENTS_PER_PAGE = 5
MENU_PHOTO_PATH = "assets/menu.jpg"

AGREEMENT_TEXT = """
📜 <b>Пользовательское соглашение</b>

Добро пожаловать в бот «КудаБали»!

1️⃣ Все материалы предоставляются в ознакомительных целях
2️⃣ Администрация не гарантирует точность информации
3️⃣ Администрация не несёт ответственности за качество мероприятий

Нажимая «✅ Соглашаюсь», вы принимаете условия.
"""

PLACES_CATEGORIES = [
    ("🍽 Рестораны Чангу", "restaurants_canggu"),
    ("🍽 Рестораны Семиньяк", "restaurants_seminyak"),
    ("🍽 Рестораны Убуд", "restaurants_ubud"),
    ("🍽 Рестораны Улувату", "restaurants_uluwatu"),
    ("🏖 Пляжи", "beaches"),
    ("💻 Коворкинги", "coworkings"),
    ("🛕 Храмы", "temples"),
    ("💧 Водопады", "waterfalls"),
    ("🏄 Серф-споты", "surf_spots"),
    ("🧘 Йога", "yoga"),
    ("💆 Спа", "spas"),
    ("🎉 Клубы", "clubs"),
]


async def log_action(user_id: int, action: str):
    async with AsyncSessionMaker() as session:
        session.add(UserAction(telegram_id=user_id, action=action))
        await session.commit()


# === AGREEMENT ===
async def get_agreement_data(**kwargs):
    return {"agreement_text": AGREEMENT_TEXT}

async def on_agree_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    user_id = callback.from_user.id
    await log_action(user_id, "agree")
    async with AsyncSessionMaker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if not user:
            user = User(telegram_id=user_id, agreed=True)
            session.add(user)
        else:
            user.agreed = True
        await session.commit()
    await manager.switch_to(FeedMenuStates.main)


# === MAIN MENU ===
async def get_main_menu_data(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    await log_action(user_id, "menu")
    has_photo = os.path.exists(MENU_PHOTO_PATH)
    return {
        "title": "🌴 КудаБали",
        "subtitle": "Афиша событий • Гид по острову • Отзывы из чатов",
        "has_photo": has_photo,
        "photo_path": MENU_PHOTO_PATH if has_photo else None
    }

async def on_events_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    await log_action(callback.from_user.id, "events_menu")
    manager.dialog_data["events_mode"] = True
    await manager.switch_to(FeedMenuStates.category)

async def on_ai_chat_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    await log_action(callback.from_user.id, "ai_chat")
    manager.dialog_data["chat_history"] = []
    await manager.switch_to(FeedMenuStates.ai_chat)

async def on_places_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    await log_action(callback.from_user.id, "places_menu")
    await manager.switch_to(FeedMenuStates.places_menu)

async def on_suggest_click(callback: CallbackQuery, button: Button, manager: DialogManager):
    await log_action(callback.from_user.id, "suggest_open")
    await manager.switch_to(FeedMenuStates.suggest)

async def on_back_to_menu(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.switch_to(FeedMenuStates.main)


# === EVENTS ===
async def get_events_menu_data(**kwargs):
    return {"title": "🎉 Афиша событий"}

async def on_category_selected(callback: CallbackQuery, button: Button, manager: DialogManager):
    category = button.widget_id
    await log_action(callback.from_user.id, f"cat_{category}")
    manager.dialog_data["selected_category"] = category
    manager.dialog_data["events_mode"] = True
    await manager.switch_to(FeedMenuStates.category)

async def get_category_events(dialog_manager: DialogManager, **kwargs):
    category = dialog_manager.dialog_data.get("selected_category", "All")
    scroll = dialog_manager.find("events_pages")
    page = await scroll.get_page() if scroll else 0

    async with AsyncSessionMaker() as session:
        today = date.today()
        base_query = select(ScrapedEvent).where(ScrapedEvent.status == "approved")

        if category != "All":
            base_query = base_query.where(ScrapedEvent.category == category)
        else:
            base_query = base_query.where(ScrapedEvent.category.notin_(["Spam", "Unknown"]))

        base_query = base_query.where(
            or_(ScrapedEvent.event_date >= today, ScrapedEvent.event_date.is_(None))
        )

        total_count = await session.scalar(select(func.count()).select_from(base_query.subquery()))
        total_pages = max(1, math.ceil((total_count or 0) / EVENTS_PER_PAGE))

        events_query = base_query.order_by(
            ScrapedEvent.event_date.asc().nulls_last(),
            ScrapedEvent.created_at.desc()
        ).limit(EVENTS_PER_PAGE).offset(page * EVENTS_PER_PAGE)

        result = await session.execute(events_query)
        events = result.scalars().all()

    if not events:
        events_text = "📭 Пока пусто"
    else:
        lines = []
        for e in events:
            date_str = e.event_date.strftime("%d.%m") if e.event_date else "—"
            summary = e.summary or "Без названия"
            link = e.link or "#"
            cat_icon = CATEGORY_ICONS.get(e.category, "") if category == "All" else ""
            lines.append(f"📅 <b>{date_str}</b> {cat_icon} <a href='{link}'>{summary}</a>")
        events_text = "\n\n".join(lines)

    cat_name = "Все события" if category == "All" else category
    icon = "📋" if category == "All" else CATEGORY_ICONS.get(category, "📁")

    return {
        "category_name": cat_name,
        "icon": icon,
        "events": events_text,
        "page_info": f"Стр. {page + 1}/{total_pages}",
        "pages": total_pages
    }


# === AI CHAT ===
async def get_ai_chat_data(**kwargs):
    return {"prompt": "💬 Спроси меня о Бали!\n\nНапример:\n• Где лучший кофе в Чангу?\n• Какой пляж для серфинга?\n• Где работать с ноутбуком?"}

async def on_ai_message(message: Message, widget: MessageInput, manager: DialogManager):
    user_text = message.text or ""
    await log_action(message.from_user.id, "ai_question")
    
    # Получаем историю
    history = manager.dialog_data.get("chat_history", [])
    
    # Отправляем "печатает..."
    thinking = await message.answer("🤔 Думаю...")
    
    # Получаем ответ
    response = await get_ai_response(user_text, history)
    
    # Удаляем "печатает..."
    await thinking.delete()
    
    # Сохраняем в историю
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": response})
    manager.dialog_data["chat_history"] = history[-10:]  # Храним последние 10
    
    await message.answer(response, parse_mode="HTML")


# === PLACES ===
async def get_places_menu_data(**kwargs):
    return {
        "title": "📍 Места на Бали",
        "categories": PLACES_CATEGORIES
    }

async def on_places_category_selected(callback: CallbackQuery, widget, manager: DialogManager, item_id: str):
    await log_action(callback.from_user.id, f"places_{item_id}")
    manager.dialog_data["places_category"] = item_id
    # Сбрасываем страницу на первую
    scroll = manager.find("places_pages")
    if scroll:
        await scroll.set_page(0)
    await manager.switch_to(FeedMenuStates.places_list)

async def get_places_list_data(dialog_manager: DialogManager, **kwargs):
    import json
    import math
    from pathlib import Path
    
    category = dialog_manager.dialog_data.get("places_category", "beaches")
    PLACES_PER_PAGE = 10
    
    # Получаем текущую страницу
    scroll = dialog_manager.find("places_pages")
    page = await scroll.get_page() if scroll else 0
    
    json_path = Path("knowledge_base") / f"{category}.json"
    places = []
    if json_path.exists():
        with open(json_path, encoding='utf-8') as f:
            places = json.load(f)
    
    if not places:
        text = "📭 Нет данных"
        total_pages = 1
    else:
        # Сортируем: проверенные первыми
        places = sorted(places, key=lambda x: (not x.get("verified", False), x.get("name", "")))
        
        total_pages = max(1, math.ceil(len(places) / PLACES_PER_PAGE))
        
        # Берём срез для текущей страницы
        start = page * PLACES_PER_PAGE
        end = start + PLACES_PER_PAGE
        page_places = places[start:end]
        
        lines = []
        for p in page_places:
            name = p.get("name", "")
            if not name:
                continue
            
            desc = p.get("description", "")
            price = p.get("price", "")
            verified = p.get("verified", False)
            
            # Зелёная галочка для проверенных
            mark = "✅ " if verified else ""
            line = f"{mark}<b>{name}</b>"
            
            if price:
                line += f" • {price}"
            
            # Описание
            if desc and len(desc) > 5 and len(desc) < 120:
                line += f"\n{desc}"
            
            
            # Ссылки на обсуждения
            mentions = p.get("mentions", [])
            if mentions:
                links = " ".join([f"<a href=\"{m['link']}\">💬{i}</a>" for i, m in enumerate(mentions[:3], 1)])
                line += f"\nОбсуждения: {links}"
            lines.append(line)
        
        text = "\n\n".join(lines)
    
    cat_name = next((name for name, key in PLACES_CATEGORIES if key == category), category)
    
    return {
        "category_name": cat_name,
        "places_text": text,
        "pages": total_pages,
        "page_info": f"Стр. {page + 1}/{total_pages}"
    }


# === SUGGEST ===
async def on_suggest_input(message: Message, widget: MessageInput, manager: DialogManager):
    text = message.text or ""
    if len(text) < 10:
        await message.answer("❌ Слишком короткое сообщение")
        return
    
    await log_action(message.from_user.id, "suggest_send")
    
    async with AsyncSessionMaker() as session:
        ev = ScrapedEvent(
            chat_title="user_suggest",
            link=f"user:{message.from_user.id}:{message.message_id}",
            raw_text=text,
            text_hash=compute_text_hash(text),
            status="review",
            category="Unknown",
            summary=text[:100]
        )
        session.add(ev)
        await session.commit()
    
    await message.answer("✅ Спасибо! Событие отправлено на модерацию.")
    await manager.switch_to(FeedMenuStates.main)


# === WINDOWS ===

agreement_window = Window(
    Format("{agreement_text}"),
    Button(Const("✅ Соглашаюсь"), id="agree", on_click=on_agree_click),
    state=FeedMenuStates.agreement,
    getter=get_agreement_data,
    parse_mode="HTML"
)

main_menu_window = Window(
    StaticMedia(path=Format("{photo_path}"), type=ContentType.PHOTO, when="has_photo"),
    Format("<b>{title}</b>\n{subtitle}"),
    Column(
        Button(Const("🎉 Афиша событий"), id="events", on_click=on_events_click),
        Button(Const("💬 Спросить про Бали"), id="ai_chat", on_click=on_ai_chat_click),
        Button(Const("📍 Места"), id="places", on_click=on_places_click),
        Button(Const("💡 Предложить событие"), id="suggest", on_click=on_suggest_click),
    ),
    state=FeedMenuStates.main,
    getter=get_main_menu_data,
    parse_mode="HTML"
)

category_window = Window(
    Format("{icon} <b>{category_name}</b>\n\n{events}\n\n{page_info}"),
    StubScroll(id="events_pages", pages="pages"),
    Row(NumberedPager(scroll="events_pages")),
    Row(
        Button(Const("🆓 Free"), id="Free", on_click=on_category_selected),
        Button(Const("💰 Paid"), id="Paid", on_click=on_category_selected),
    ),
    Row(
        Button(Const("🤝 Networking"), id="Networking", on_click=on_category_selected),
        Button(Const("🎉 Party"), id="Party", on_click=on_category_selected),
    ),
    Button(Const("📋 Все"), id="All", on_click=on_category_selected),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.category,
    getter=get_category_events,
    parse_mode="HTML"
)

ai_chat_window = Window(
    Format("{prompt}"),
    MessageInput(on_ai_message),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.ai_chat,
    getter=get_ai_chat_data,
    parse_mode="HTML"
)

places_menu_window = Window(
    Const("📍 <b>Выбери категорию:</b>"),
    Column(
        Select(
            Format("{item[0]}"),
            id="places_cat",
            item_id_getter=lambda x: x[1],
            items="categories",
            on_click=on_places_category_selected,
        ),
    ),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.places_menu,
    getter=get_places_menu_data,
    parse_mode="HTML"
)

places_list_window = Window(
    Format("📍 <b>{category_name}</b>\n\n{places_text}\n\n{page_info}\n\n<i>✅ — проверено пользователями</i>"),
    StubScroll(id="places_pages", pages="pages"),
    Row(NumberedPager(scroll="places_pages")),
    Button(Const("🔙 Назад"), id="back_places", on_click=lambda c, b, m: m.switch_to(FeedMenuStates.places_menu)),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.places_list,
    getter=get_places_list_data,
    parse_mode="HTML"
)

suggest_window = Window(
    Const("💡 <b>Предложить событие</b>\n\nОтправьте описание одним сообщением:"),
    MessageInput(on_suggest_input),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.suggest,
    parse_mode="HTML"
)

feed_dialog = Dialog(
    agreement_window,
    main_menu_window,
    category_window,
    ai_chat_window,
    places_menu_window,
    places_list_window,
    suggest_window,
)
