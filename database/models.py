"""
Объявления ORM-моделей. Этот файл не создаёт engine/session —
только таблицы. Так alembic может импортировать его без .env.
"""
from datetime import datetime, timezone
import hashlib

from sqlalchemy import Boolean, Column, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

from data.statuses import EventStatus


class Base(DeclarativeBase):
    pass


class ScrapedEvent(Base):
    __tablename__ = "scraped_events"

    id = Column(Integer, primary_key=True)
    chat_title = Column(String)
    link = Column(String, index=True)
    raw_text = Column(Text)
    text_hash = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default=EventStatus.PENDING, index=True)
    category = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    event_date = Column(Date, nullable=True, index=True)
    is_recurring = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_category_date", "category", "event_date"),
    )


class BaliChat(Base):
    __tablename__ = "bali_chats"

    id = Column(Integer, primary_key=True)
    chat_id = Column(String, unique=True, index=True)
    title = Column(String)
    username = Column(String, nullable=True)
    link = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_scan = Column(DateTime, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    agreed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PlaceReview(Base):
    __tablename__ = "place_reviews"

    id = Column(Integer, primary_key=True)
    place_name = Column(String, index=True)
    mentioned_name = Column(String)
    chat_title = Column(String)
    username = Column(String)
    message_text = Column(String)
    sentiment = Column(String)
    link = Column(String)
    message_date = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, index=True)
    action = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def compute_text_hash(text: str) -> str:
    normalized = text.lower().strip()[:500]
    return hashlib.sha256(normalized.encode()).hexdigest()
