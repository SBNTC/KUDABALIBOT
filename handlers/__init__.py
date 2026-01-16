"""Главный роутер"""
from aiogram import Router
from .user import get_user_router


def get_main_router() -> Router:
    """Объединяем все роутеры"""
    router = Router()
    router.include_router(get_user_router())
    return router
