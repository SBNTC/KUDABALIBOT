from aiogram import Router
from . import start, digest, stats


def get_user_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(digest.router)
    router.include_router(stats.router)
    return router
