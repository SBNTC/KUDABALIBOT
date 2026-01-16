from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy import select

from states import FeedMenuStates
from database.models import AsyncSessionMaker, User

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, dialog_manager: DialogManager):
    user_id = message.from_user.id
    
    # Проверяем, согласился ли пользователь
    async with AsyncSessionMaker() as session:
        user = await session.scalar(
            select(User).where(User.telegram_id == user_id)
        )
        
        if user and user.agreed:
            # Уже согласился — показываем меню
            await dialog_manager.start(FeedMenuStates.main, mode=StartMode.RESET_STACK)
        else:
            # Новый пользователь — показываем соглашение
            await dialog_manager.start(FeedMenuStates.agreement, mode=StartMode.RESET_STACK)
