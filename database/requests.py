from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import ScrapedEvent, compute_text_hash, AsyncSessionMaker

# --- GET (Получение) ---

async def get_all_events(session: AsyncSession, search_query: str = None, category_filter: str = None):
    stmt = select(ScrapedEvent).order_by(ScrapedEvent.created_at.desc())
    if category_filter:
        stmt = stmt.where(ScrapedEvent.category == category_filter)
    if search_query:
        q = f"%{search_query}%"
        stmt = stmt.where(
            or_(
                ScrapedEvent.chat_title.ilike(q),
                ScrapedEvent.summary.ilike(q),
                ScrapedEvent.raw_text.ilike(q)
            )
        )
    result = await session.execute(stmt)
    return result.scalars().all()

async def get_event_by_id(session: AsyncSession, event_id: int):
    return await session.get(ScrapedEvent, event_id)

# --- UPDATE (Обновление) ---

async def update_event_status(session: AsyncSession, event_id: int, new_status: str) -> None:
    stmt = update(ScrapedEvent).where(ScrapedEvent.id == event_id).values(status=new_status)
    await session.execute(stmt)
    await session.commit()

async def update_event_category(session: AsyncSession, event_id: int, new_category: str):
    stmt = update(ScrapedEvent).where(ScrapedEvent.id == event_id).values(category=new_category)
    await session.execute(stmt)
    await session.commit()

async def update_event_date(session: AsyncSession, event_id: int, new_date):
    stmt = update(ScrapedEvent).where(ScrapedEvent.id == event_id).values(event_date=new_date)
    await session.execute(stmt)
    await session.commit()

async def update_event_summary(session: AsyncSession, event_id: int, new_summary: str):
    stmt = update(ScrapedEvent).where(ScrapedEvent.id == event_id).values(summary=new_summary)
    await session.execute(stmt)
    await session.commit()

# --- DELETE (Удаление) ---

async def delete_event_by_id(session: AsyncSession, event_id: int):
    stmt = delete(ScrapedEvent).where(ScrapedEvent.id == event_id)
    await session.execute(stmt)
    await session.commit()

# --- CREATE (Создание) ---

async def create_manual_event(
    session: AsyncSession,
    summary: str,
    category: str,
    event_date: Optional[date],
    link: Optional[str] = None,
) -> int:
    unique_id = uuid4().hex
    if not link:
        link = f"manual:{unique_id}"

    # Добавляем уникальный ID в raw_text, чтобы text_hash всегда был разным
    # Пользователь увидит summary, а raw_text только в админке
    raw_text = f"MANUAL_EVENT_ID:{unique_id}\n{summary}"
    text_hash = compute_text_hash(raw_text)

    ev = ScrapedEvent(
        chat_title="manual",
        link=link,
        raw_text=raw_text,
        text_hash=text_hash,
        status="approved",
        category=category,
        summary=summary,
        event_date=event_date,
        is_recurring=False,
    )
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return int(ev.id)
