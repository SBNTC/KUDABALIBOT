"""Инициализация Bot и Dispatcher (точка входа для всех модулей)"""
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config

# Инициализация бота
bot = Bot(
    token=config.bot_token.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Dispatcher с хранилищем состояний
dp = Dispatcher(storage=MemoryStorage())
