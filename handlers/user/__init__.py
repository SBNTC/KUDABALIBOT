from aiogram import Router
from . import start, digest, stats, admin

def get_user_router() -> Router:
    router = Router()
    router.include_router(start.router)
    # router.include_router(feed.router)  <-- Убрали feed
    router.include_router(digest.router)
    router.include_router(stats.router)
    router.include_router(admin.router)
    return router
