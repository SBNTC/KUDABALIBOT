"""
Дедупликация pending / review событий.

  1. exact_dedup() — удаляет точные совпадения по raw_text.
  2. fuzzy_dedup() — удаляет события, у которых первые 200 символов
     совпадают с другим > 80% (difflib.SequenceMatcher).

Обе функции безопасны для периодического вызова из scheduler'а.
"""
import logging
from difflib import SequenceMatcher
from sqlalchemy import select, delete

from database.models import ScrapedEvent
from data.statuses import EventStatus
from database.session import AsyncSessionMaker


logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 0.80
FUZZY_PREFIX = 200


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.lower().split())[:FUZZY_PREFIX]


async def exact_dedup(statuses: tuple[str, ...] = (EventStatus.PENDING, EventStatus.REVIEW)) -> int:
    """Удаляет точные дубликаты raw_text внутри указанных статусов."""
    removed = 0
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(ScrapedEvent)
            .where(ScrapedEvent.status.in_(statuses))
            .where(ScrapedEvent.raw_text.isnot(None))
            .order_by(ScrapedEvent.created_at.desc())
        )
        events = result.scalars().all()

        seen: set[str] = set()
        to_delete: list[int] = []
        for ev in events:
            key = (ev.raw_text or "").strip()
            if key in seen:
                to_delete.append(ev.id)
            else:
                seen.add(key)

        if to_delete:
            await session.execute(
                delete(ScrapedEvent).where(ScrapedEvent.id.in_(to_delete))
            )
            await session.commit()
            removed = len(to_delete)

    if removed:
        logger.info(f"🧹 exact_dedup: удалено {removed}")
    return removed


_FUZZY_MAX_EVENTS = 2000  # O(n²) — ограничиваем окно во избежание лагов


async def fuzzy_dedup(
    statuses: tuple[str, ...] = (EventStatus.PENDING, EventStatus.REVIEW),
    threshold: float = FUZZY_THRESHOLD,
) -> int:
    """
    Удаляет сообщения, похожие на другие по первым FUZZY_PREFIX символам.
    Оставляет самое старое (первое встреченное) — у него больше шансов быть
    оригиналом. Обрабатывает не более _FUZZY_MAX_EVENTS за один прогон.
    """
    removed = 0
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(ScrapedEvent)
            .where(ScrapedEvent.status.in_(statuses))
            .where(ScrapedEvent.raw_text.isnot(None))
            .order_by(ScrapedEvent.created_at.asc())
            .limit(_FUZZY_MAX_EVENTS)
        )
        events = result.scalars().all()

        kept: list[tuple[int, str]] = []
        to_delete: list[int] = []

        for ev in events:
            norm = _normalize(ev.raw_text)
            if not norm:
                continue
            duplicate = False
            for _, kept_norm in kept:
                if SequenceMatcher(None, norm, kept_norm).ratio() >= threshold:
                    duplicate = True
                    break
            if duplicate:
                to_delete.append(ev.id)
            else:
                kept.append((ev.id, norm))

        if to_delete:
            await session.execute(
                delete(ScrapedEvent).where(ScrapedEvent.id.in_(to_delete))
            )
            await session.commit()
            removed = len(to_delete)

    if removed:
        logger.info(f"🧹 fuzzy_dedup: удалено {removed}")
    return removed


async def run_full_dedup() -> int:
    """Полная дедупликация: exact → fuzzy."""
    total = await exact_dedup()
    total += await fuzzy_dedup()
    return total
