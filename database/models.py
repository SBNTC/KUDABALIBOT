from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index, Date
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from datetime import datetime, timezone
import hashlib
from config import config


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
    status = Column(String, default="pending", index=True)
    category = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    event_date = Column(Date, nullable=True, index=True)  # Дата события
    is_recurring = Column(Boolean, default=False)  # Пробные/регулярные
    
    __table_args__ = (
        Index('idx_category_date', 'category', 'event_date'),
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


def compute_text_hash(text: str) -> str:
    normalized = text.lower().strip()[:500]
    return hashlib.sha256(normalized.encode()).hexdigest()


engine = create_async_engine(config.database_url)
AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    agreed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PlaceReview(Base):
    __tablename__ = "place_reviews"
    
    id = Column(Integer, primary_key=True)
    place_name = Column(String, index=True)      # Нормализованное название места
    mentioned_name = Column(String)               # Как упомянули в чате
    chat_title = Column(String)                   # Название чата
    username = Column(String)                     # @username автора
    message_text = Column(String)                 # Релевантная часть сообщения
    sentiment = Column(String)                    # positive/negative/neutral
    link = Column(String)                         # Ссылка на сообщение
    message_date = Column(DateTime)               # Дата сообщения
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserAction(Base):
    __tablename__ = "user_actions"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, index=True)
    action = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
