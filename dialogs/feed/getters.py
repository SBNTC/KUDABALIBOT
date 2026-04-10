"""Data-getter'ы для windows feed-диалога."""
import json
import math
import os
from datetime import date
from pathlib import Path

from aiogram_dialog import DialogManager
from sqlalchemy import select, func, or_

from database.models import ScrapedEvent, User
from database.session import AsyncSessionMaker
from data.categories import CATEGORY_ICONS
from data.statuses import EventStatus
from dialogs.feed.constants import (
    AGREEMENT_TEXT, EVENTS_PER_PAGE, PLACES_CATEGORIES, PLACES_PER_PAGE, MENU_PHOTO_PATH
)


async def get_agreement_data(**kwargs) -> dict:
    return {"agreement_text": AGREEMENT_TEXT}


async def get_main_menu_data(dialog_manager: DialogManager, **kwargs) -> dict:
    has_photo = os.path.exists(MENU_PHOTO_PATH)
    return {
        "title": "🌴 КудаБали",
        "subtitle": "Афиша событий • Гид по острову • Отзывы из чатов",
        "has_photo": has_photo,
        "photo_path": MENU_PHOTO_PATH if has_photo else None,
    }


async def get_category_events(dialog_manager: DialogManager, **kwargs) -> dict:
    category = dialog_manager.dialog_data.get("selected_category", "All")
    scroll = dialog_manager.find("events_pages")
    page = await scroll.get_page() if scroll else 0

    async with AsyncSessionMaker() as session:
        today = date.today()
        base_query = select(ScrapedEvent).where(ScrapedEvent.status == EventStatus.APPROVED)

        if category != "All":
            base_query = base_query.where(ScrapedEvent.category == category)
        else:
            base_query = base_query.where(ScrapedEvent.category.notin_(["Spam", "Unknown"]))

        base_query = base_query.where(
            or_(ScrapedEvent.event_date >= today, ScrapedEvent.event_date.is_(None))
        )

        total_count = await session.scalar(
            select(func.count()).select_from(base_query.subquery())
        )
        total_pages = max(1, math.ceil((total_count or 0) / EVENTS_PER_PAGE))

        events_query = (
            base_query
            .order_by(ScrapedEvent.event_date.asc().nulls_last(), ScrapedEvent.created_at.desc())
            .limit(EVENTS_PER_PAGE)
            .offset(page * EVENTS_PER_PAGE)
        )
        result = await session.execute(events_query)
        events = result.scalars().all()

    if not events:
        events_text = "📭 Пока пусто"
    else:
        lines = []
        for e in events:
            date_str = e.event_date.strftime("%d.%m") if e.event_date else "—"
            summary = e.summary or "Без названия"
            link = e.link or "#"
            cat_icon = CATEGORY_ICONS.get(e.category, "") if category == "All" else ""
            lines.append(f"📅 <b>{date_str}</b> {cat_icon} <a href='{link}'>{summary}</a>")
        events_text = "\n\n".join(lines)

    cat_name = "Все события" if category == "All" else category
    icon = "📋" if category == "All" else CATEGORY_ICONS.get(category, "📁")

    return {
        "category_name": cat_name,
        "icon": icon,
        "events": events_text,
        "page_info": f"Стр. {page + 1}/{total_pages}",
        "pages": total_pages,
    }


async def get_ai_chat_data(**kwargs) -> dict:
    return {
        "prompt": (
            "💬 Спроси меня о Бали!\n\n"
            "Например:\n• Где лучший кофе в Чангу?\n"
            "• Какой пляж для серфинга?\n• Где работать с ноутбуком?"
        )
    }


async def get_places_menu_data(**kwargs) -> dict:
    return {"title": "📍 Места на Бали", "categories": PLACES_CATEGORIES}


async def get_places_list_data(dialog_manager: DialogManager, **kwargs) -> dict:
    category = dialog_manager.dialog_data.get("places_category", "beaches")
    scroll = dialog_manager.find("places_pages")
    page = await scroll.get_page() if scroll else 0

    json_path = Path("knowledge_base") / f"{category}.json"
    places: list = []
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            places = json.load(f)

    if not places:
        text = "📭 Нет данных"
        total_pages = 1
    else:
        places = sorted(places, key=lambda x: (not x.get("verified", False), x.get("name", "")))
        total_pages = max(1, math.ceil(len(places) / PLACES_PER_PAGE))
        page_places = places[page * PLACES_PER_PAGE : (page + 1) * PLACES_PER_PAGE]

        lines = []
        for p in page_places:
            name = p.get("name", "")
            if not name:
                continue
            mark = "✅ " if p.get("verified") else ""
            line = f"{mark}<b>{name}</b>"
            price = p.get("price", "")
            if price:
                line += f" • {price}"
            desc = p.get("description", "")
            if 5 < len(desc) < 120:
                line += f"\n{desc}"
            mentions = p.get("mentions", [])
            if mentions:
                links = " ".join(
                    f"<a href=\"{m['link']}\">💬{i}</a>"
                    for i, m in enumerate(mentions[:3], 1)
                )
                line += f"\nОбсуждения: {links}"
            lines.append(line)
        text = "\n\n".join(lines)

    cat_name = next((n for n, k in PLACES_CATEGORIES if k == category), category)
    return {
        "category_name": cat_name,
        "places_text": text,
        "pages": total_pages,
        "page_info": f"Стр. {page + 1}/{total_pages}",
    }
