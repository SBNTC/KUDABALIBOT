"""Window-определения и сборка Dialog."""
from aiogram.types import ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, NumberedPager, Row, Select, StubScroll
from aiogram_dialog.widgets.media import StaticMedia
from aiogram_dialog.widgets.text import Const, Format

from states import FeedMenuStates
from dialogs.feed.getters import (
    get_agreement_data,
    get_ai_chat_data,
    get_category_events,
    get_main_menu_data,
    get_places_list_data,
    get_places_menu_data,
)
from dialogs.feed.handlers import (
    on_agree_click,
    on_ai_message,
    on_back_to_menu,
    on_category_selected,
    on_events_click,
    on_ai_chat_click,
    on_places_click,
    on_places_category_selected,
    on_suggest_click,
    on_suggest_input,
)

agreement_window = Window(
    Format("{agreement_text}"),
    Button(Const("✅ Соглашаюсь"), id="agree", on_click=on_agree_click),
    state=FeedMenuStates.agreement,
    getter=get_agreement_data,
    parse_mode="HTML",
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
    parse_mode="HTML",
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
    parse_mode="HTML",
)

ai_chat_window = Window(
    Format("{prompt}"),
    MessageInput(on_ai_message),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.ai_chat,
    getter=get_ai_chat_data,
    parse_mode="HTML",
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
    parse_mode="HTML",
)

places_list_window = Window(
    Format("📍 <b>{category_name}</b>\n\n{places_text}\n\n{page_info}\n\n<i>✅ — проверено пользователями</i>"),
    StubScroll(id="places_pages", pages="pages"),
    Row(NumberedPager(scroll="places_pages")),
    Button(Const("🔙 Назад"), id="back_places", on_click=lambda c, b, m: m.switch_to(FeedMenuStates.places_menu)),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.places_list,
    getter=get_places_list_data,
    parse_mode="HTML",
)

suggest_window = Window(
    Const("💡 <b>Предложить событие</b>\n\nОтправьте описание одним сообщением:"),
    MessageInput(on_suggest_input),
    Button(Const("🏠 Меню"), id="back", on_click=on_back_to_menu),
    state=FeedMenuStates.suggest,
    parse_mode="HTML",
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
