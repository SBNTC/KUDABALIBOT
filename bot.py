import asyncio
import logging
from aiogram_dialog import setup_dialogs
from loader import bot, dp
from database.models import init_db
from handlers import get_main_router
from middlewares import DbSessionMiddleware
from services.scheduler import setup_scheduler
from dialogs.feed_menu import feed_dialog

# Подключаем НАШУ новую админку
from handlers.admin_panel import admin_router

async def main():
    # Настройка логов
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logging.info("🤖 Запуск бота...")

    await init_db()
    
    # Middleware
    dp.update.middleware(DbSessionMiddleware())
    
    # --- РЕГИСТРАЦИЯ РОУТЕРОВ ---
    # Важен порядок! Специфичные роутеры (админка) должны быть выше общих.
    
    dp.include_router(admin_router)   # 1. Сначала админка
    dp.include_router(feed_dialog)    # 2. Меню пользователя
    dp.include_router(get_main_router()) # 3. Основные хендлеры (start и т.д.)
    
    setup_dialogs(dp)
    await setup_scheduler()
    
    logging.info("✅ Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: 
        asyncio.run(main())
    except KeyboardInterrupt: 
        pass
