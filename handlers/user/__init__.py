from aiogram import Router
from . import start, digest


def get_user_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(digest.router)
    return router
