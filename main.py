import asyncio, logging, os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from database.base import init_db
from handlers.user import router as user_router
from dialogs.events_menu import dialog
from services.chat_listener import start_telethon, client as telethon_client

async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    await init_db()
    
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(user_router)
    dp.include_router(dialog)
    setup_dialogs(dp)
    
    asyncio.create_task(start_telethon())
    print("✅ Bot started!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await telethon_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
