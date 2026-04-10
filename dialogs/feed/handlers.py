"""Click-хендлеры для feed-диалога."""
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput
from sqlalchemy import select

from database.models import ScrapedEvent, User, UserAction, compute_text_hash
from database.session import AsyncSessionMaker
from data.statuses import EventStatus
from states import FeedMenuStates
from services.ai_assistant import get_ai_response


async def log_action(user_id: int, action: str) -> None:
    async with AsyncSessionMaker() as session:
        session.add(UserAction(telegram_id=user_id, action=action))
        await session.commit()


# === AGREEMENT ===

async def on_agree_click(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    user_id = callback.from_user.id
    await log_action(user_id, "agree")
    async with AsyncSessionMaker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if not user:
            user = User(telegram_id=user_id, agreed=True)
            session.add(user)
        else:
            user.agreed = True
        await session.commit()
    await manager.switch_to(FeedMenuStates.main)


# === MAIN MENU ===

async def on_events_click(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    await log_action(callback.from_user.id, "events_menu")
    manager.dialog_data["selected_category"] = "All"
    await manager.switch_to(FeedMenuStates.category)


async def on_ai_chat_click(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    await log_action(callback.from_user.id, "ai_chat")
    manager.dialog_data["chat_history"] = []
    await manager.switch_to(FeedMenuStates.ai_chat)


async def on_places_click(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    await log_action(callback.from_user.id, "places_menu")
    await manager.switch_to(FeedMenuStates.places_menu)


async def on_suggest_click(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    await log_action(callback.from_user.id, "suggest_open")
    await manager.switch_to(FeedMenuStates.suggest)


async def on_back_to_menu(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    await manager.switch_to(FeedMenuStates.main)


# === EVENTS ===

async def on_category_selected(callback: CallbackQuery, button: Button, manager: DialogManager) -> None:
    category = button.widget_id
    await log_action(callback.from_user.id, f"cat_{category}")
    manager.dialog_data["selected_category"] = category
    await manager.switch_to(FeedMenuStates.category)


# === AI CHAT ===

async def on_ai_message(message: Message, widget: MessageInput, manager: DialogManager) -> None:
    user_text = message.text or ""
    await log_action(message.from_user.id, "ai_question")

    history = manager.dialog_data.get("chat_history", [])
    thinking = await message.answer("🤔 Думаю...")

    response = await get_ai_response(user_text, history)
    await thinking.delete()

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": response})
    manager.dialog_data["chat_history"] = history[-10:]

    await message.answer(response, parse_mode="HTML")


# === PLACES ===

async def on_places_category_selected(
    callback: CallbackQuery, widget, manager: DialogManager, item_id: str
) -> None:
    await log_action(callback.from_user.id, f"places_{item_id}")
    manager.dialog_data["places_category"] = item_id
    scroll = manager.find("places_pages")
    if scroll:
        await scroll.set_page(0)
    await manager.switch_to(FeedMenuStates.places_list)


# === SUGGEST ===

async def on_suggest_input(message: Message, widget: MessageInput, manager: DialogManager) -> None:
    text = message.text or ""
    if len(text) < 10:
        await message.answer("❌ Слишком короткое сообщение")
        return

    await log_action(message.from_user.id, "suggest_send")
    async with AsyncSessionMaker() as session:
        ev = ScrapedEvent(
            chat_title="user_suggest",
            link=f"user:{message.from_user.id}:{message.message_id}",
            raw_text=text,
            text_hash=compute_text_hash(text),
            status=EventStatus.REVIEW,
            category="Unknown",
            summary=text[:100],
        )
        session.add(ev)
        await session.commit()

    await message.answer("✅ Спасибо! Событие отправлено на модерацию.")
    await manager.switch_to(FeedMenuStates.main)
