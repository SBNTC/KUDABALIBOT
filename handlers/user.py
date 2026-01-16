from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from dialogs.events_menu import EventsSG

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(EventsSG.menu, mode=StartMode.RESET_STACK)
