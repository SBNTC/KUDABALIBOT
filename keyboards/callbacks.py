from aiogram.filters.callback_data import CallbackData


class FeedCallback(CallbackData, prefix="feed"):
    category: str
    page: int = 1


class MenuCallback(CallbackData, prefix="menu"):
    action: str
