import asyncio
import logging
from aiogram_dialog import setup_dialogs
from logging_config import setup_logging
from loader import bot, dp
from handlers import get_main_router
from middlewares import ThrottlingMiddleware
from services.scheduler import setup_scheduler, scheduler
from services.telethon_client import close_client
from dialogs.feed import feed_dialog
from handlers.admin_panel import admin_router
from database.session import engine, init_db


async def main() -> None:
    setup_logging()
    logging.info("🤖 Запуск бота...")

    await init_db()

    dp.message.middleware(ThrottlingMiddleware())

    # Порядок важен: специфичные роутеры (админка) выше общих
    dp.include_router(admin_router)
    dp.include_router(feed_dialog)
    dp.include_router(get_main_router())

    setup_dialogs(dp)
    await setup_scheduler()

    logging.info("✅ Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        logging.info("🛑 Завершение работы...")
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await close_client()
        await bot.session.close()
        await engine.dispose()
        logging.info("✅ Остановлено чисто.")


if __name__ == "__main__":
    try:
        import uvloop  # type: ignore[import]
        uvloop.run(main())
    except ImportError:
        # uvloop не поддерживается на Windows — используем стандартный loop
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
