from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .callbacks import FeedCallback, MenuCallback

CATEGORY_NAMES = {
    "All": "📋 Все события",
    "Free": "🎉 Бесплатно",
    "Paid": "💰 Платно",
    "Networking": "🤝 Нетворкинг",
    "Party": "🎵 Вечеринки",
}


def get_main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Все", callback_data=FeedCallback(category="All"))
    builder.button(text="🎉 Бесплатно", callback_data=FeedCallback(category="Free"))
    builder.button(text="💰 Платно", callback_data=FeedCallback(category="Paid"))
    builder.button(text="🤝 Нетворкинг", callback_data=FeedCallback(category="Networking"))
    builder.button(text="🎵 Вечеринки", callback_data=FeedCallback(category="Party"))
    builder.button(text="➕ Предложить", callback_data=MenuCallback(action="suggest"))
    builder.adjust(1, 2, 2, 1)
    return builder.as_markup()


def get_feed_kb(category: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if page > 1:
        builder.button(text="◀️", callback_data=FeedCallback(category=category, page=page - 1))
    if page < total_pages:
        builder.button(text="▶️", callback_data=FeedCallback(category=category, page=page + 1))
    
    builder.button(text="🏠 Меню", callback_data=MenuCallback(action="main"))
    
    if page > 1 and page < total_pages:
        builder.adjust(2, 1)
    else:
        builder.adjust(1, 1)
    
    return builder.as_markup()


def get_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=MenuCallback(action="main"))
    return builder.as_markup()
