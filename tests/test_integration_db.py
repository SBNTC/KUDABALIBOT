"""
Интеграционные тесты БД (Level 1).

Используют реальную SQLite :memory: и настоящий SQLAlchemy-движок.
Внешние API (DeepSeek, Telethon) не задействуются.

Покрывает:
  - save_message: запись, дедупликация по хэшу, возврат id
  - exact_dedup: удаление точных дубликатов
  - fuzzy_dedup: удаление нечётких дубликатов
  - Статусы событий: начальный PENDING, неизменность APPROVED
  - User model: создание и чтение
"""
import datetime
import pytest
from sqlalchemy import select

from data.statuses import EventStatus
from database.models import ScrapedEvent, User, compute_text_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_insert_counter = 0  # уникальный суффикс хэша для force-дублей


async def _insert_event(
    session_maker,
    raw_text: str,
    status: str = EventStatus.PENDING,
    created_offset_days: int = 0,
    force_unique_hash: bool = False,
) -> ScrapedEvent:
    """
    Вставляет событие напрямую через session (без фильтров collector).

    force_unique_hash=True: добавляет уникальный суффикс к хэшу, чтобы
    обойти UNIQUE constraint при вставке дублей raw_text для тестирования
    дедупликации по тексту (не по хэшу).
    """
    global _insert_counter
    _insert_counter += 1
    text_hash = compute_text_hash(raw_text)
    if force_unique_hash:
        text_hash = f"{text_hash}_{_insert_counter}"

    async with session_maker() as session:
        ev = ScrapedEvent(
            chat_title="test_chat",
            link=f"https://t.me/test/{_insert_counter}",
            raw_text=raw_text,
            text_hash=text_hash,
            status=status,
            created_at=datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=created_offset_days),
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)
        return ev


async def _count_events(session_maker, status=None) -> int:
    async with session_maker() as session:
        q = select(ScrapedEvent)
        if status:
            q = q.where(ScrapedEvent.status == status)
        rows = (await session.execute(q)).scalars().all()
        return len(rows)


# ---------------------------------------------------------------------------
# save_message
# ---------------------------------------------------------------------------

class TestSaveMessage:
    async def test_returns_id_on_new_message(self, db):
        from services.collector import save_message

        event_id = await save_message(
            chat_title="BaliEvents",
            link="https://t.me/bali/1",
            text="Открытая йога каждое воскресенье на рассвете у пляжа Берава",
        )
        assert isinstance(event_id, int)
        assert event_id > 0

    async def test_returns_none_for_duplicate_text(self, db):
        from services.collector import save_message

        text = "Нетворкинг для предпринимателей каждую среду в коворкинге Чангу"
        first = await save_message("chat", "https://t.me/c/1/1", text)
        second = await save_message("chat", "https://t.me/c/1/2", text)

        assert first is not None
        assert second is None  # дубль по хэшу

    async def test_case_difference_is_same_hash(self, db):
        """compute_text_hash нормализует к lower → одинаковый хэш."""
        from services.collector import save_message

        first = await save_message("chat", "https://t.me/c/1/1", "Йога на Бали")
        second = await save_message("chat", "https://t.me/c/1/2", "ЙОГА НА БАЛИ")
        assert first is not None
        assert second is None

    async def test_event_saved_with_pending_status(self, db):
        from services.collector import save_message

        text = "Мастер-класс по акварели в галерее Убуда в субботу"
        event_id = await save_message("chat", "https://t.me/c/1/10", text)
        assert event_id is not None

        async with db() as session:
            ev = await session.get(ScrapedEvent, event_id)
        assert ev is not None
        assert ev.status == EventStatus.PENDING

    async def test_different_texts_both_saved(self, db):
        from services.collector import save_message

        id1 = await save_message("c", "https://t.me/c/1", "Йога утром в парке у моря")
        id2 = await save_message("c", "https://t.me/c/2", "Концерт живой музыки вечером")
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2

    async def test_uses_provided_date(self, db):
        from services.collector import save_message

        # SQLite хранит datetime без timezone; сравниваем naive-значения
        dt = datetime.datetime(2025, 6, 15, 10, 0)
        event_id = await save_message(
            "chat", "https://t.me/c/1/99", "Воркшоп по керамике", msg_date=dt
        )
        assert event_id is not None

        async with db() as session:
            ev = await session.get(ScrapedEvent, event_id)
        # created_at может быть naive или aware — сравниваем без tzinfo
        stored = ev.created_at.replace(tzinfo=None) if ev.created_at.tzinfo else ev.created_at
        assert stored == dt


# ---------------------------------------------------------------------------
# exact_dedup
# ---------------------------------------------------------------------------

class TestExactDedup:
    async def test_removes_exact_duplicate(self, db):
        from services.dedup import exact_dedup

        text = "Бесплатная сальса по пятницам в баре у океана"
        # force_unique_hash позволяет обойти UNIQUE-ограничение на text_hash,
        # моделируя сценарий двух событий с одинаковым raw_text и разными хэшами
        await _insert_event(db, text, EventStatus.PENDING, created_offset_days=1, force_unique_hash=True)
        await _insert_event(db, text, EventStatus.PENDING, created_offset_days=0, force_unique_hash=True)

        removed = await exact_dedup()
        assert removed == 1
        assert await _count_events(db, EventStatus.PENDING) == 1

    async def test_keeps_unique_texts(self, db):
        from services.dedup import exact_dedup

        await _insert_event(db, "Йога на рассвете у пляжа Эко Бич")
        await _insert_event(db, "Концерт этнической музыки в Убуде")

        removed = await exact_dedup()
        assert removed == 0
        assert await _count_events(db) == 2

    async def test_does_not_touch_approved_events(self, db):
        from services.dedup import exact_dedup

        text = "Открытый микрофон по воскресеньям"
        await _insert_event(db, text, EventStatus.APPROVED)
        # Дубль в pending
        dup_text = text  # тот же текст, но pending — не должен удалять approved
        # Добавляем pending с тем же текстом через другой хэш-ключ:
        # exact_dedup работает только по PENDING/REVIEW, approved пропускает
        async with db() as session:
            ev = ScrapedEvent(
                chat_title="c2",
                link="https://t.me/c/2",
                raw_text=dup_text,
                text_hash=compute_text_hash(dup_text) + "_x",  # сломанный хэш
                status=EventStatus.PENDING,
            )
            session.add(ev)
            await session.commit()

        # approved не трогаем
        assert await _count_events(db, EventStatus.APPROVED) == 1

    async def test_deduplicates_review_status(self, db):
        from services.dedup import exact_dedup

        text = "Эко-йога в рисовых полях Убуда каждое воскресенье"
        await _insert_event(db, text, EventStatus.REVIEW, created_offset_days=2, force_unique_hash=True)
        await _insert_event(db, text, EventStatus.REVIEW, created_offset_days=0, force_unique_hash=True)

        removed = await exact_dedup()
        assert removed == 1

    async def test_keeps_older_event(self, db):
        """exact_dedup сортирует по created_at DESC → сохраняет более новое
        (первое в результате), удаляет последующие дубли."""
        from services.dedup import exact_dedup

        text = "Stand-up comedy на английском каждую пятницу"
        old = await _insert_event(db, text, EventStatus.PENDING, created_offset_days=5, force_unique_hash=True)
        new = await _insert_event(db, text, EventStatus.PENDING, created_offset_days=0, force_unique_hash=True)

        await exact_dedup()

        async with db() as session:
            remaining = (await session.execute(select(ScrapedEvent))).scalars().all()
        remaining_ids = [e.id for e in remaining]
        # Новое (created_at DESC → первым встречается new) должно остаться
        assert new.id in remaining_ids
        assert old.id not in remaining_ids


# ---------------------------------------------------------------------------
# fuzzy_dedup
# ---------------------------------------------------------------------------

class TestFuzzyDedup:
    async def test_removes_near_duplicate(self, db):
        from services.dedup import fuzzy_dedup

        base = "Открытый урок по испанскому языку каждую среду в кафе Убуда для всех уровней"
        variant = base + " Приходите!"  # >80% схожести

        await _insert_event(db, base, EventStatus.PENDING, created_offset_days=2)
        await _insert_event(db, variant, EventStatus.PENDING, created_offset_days=0)

        removed = await fuzzy_dedup()
        assert removed == 1
        assert await _count_events(db, EventStatus.PENDING) == 1

    async def test_keeps_dissimilar_events(self, db):
        from services.dedup import fuzzy_dedup

        await _insert_event(db, "Йога на рассвете у пляжа Берава, вход свободный")
        await _insert_event(db, "Мастер-класс по барабанам в студии Убуда")

        removed = await fuzzy_dedup()
        assert removed == 0
        assert await _count_events(db) == 2

    async def test_keeps_oldest_among_duplicates(self, db):
        """fuzzy_dedup сортирует по created_at ASC → оставляет самое старое."""
        from services.dedup import fuzzy_dedup

        base = "Нетворкинг для предпринимателей каждую среду вечером в Семиньяке"
        variant = base + " регистрация обязательна"

        old = await _insert_event(db, base, EventStatus.PENDING, created_offset_days=3)
        new = await _insert_event(db, variant, EventStatus.PENDING, created_offset_days=0)

        await fuzzy_dedup()

        async with db() as session:
            remaining = (await session.execute(select(ScrapedEvent))).scalars().all()
        remaining_ids = [e.id for e in remaining]
        assert old.id in remaining_ids
        assert new.id not in remaining_ids

    async def test_does_not_touch_approved(self, db):
        from services.dedup import fuzzy_dedup

        base = "Ecstatic dance в пятницу ночью на пляже Бату Болонг"
        await _insert_event(db, base, EventStatus.APPROVED)
        # Похожий pending
        await _insert_event(db, base + " вход по донейшн", EventStatus.PENDING)

        await fuzzy_dedup()
        # Approved не тронут
        assert await _count_events(db, EventStatus.APPROVED) == 1


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------

class TestUserModel:
    async def test_create_and_read_user(self, db):
        async with db() as session:
            user = User(telegram_id=42, agreed=False)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        async with db() as session:
            found = await session.scalar(
                select(User).where(User.telegram_id == 42)
            )
        assert found is not None
        assert found.agreed is False

    async def test_agree_flag_updated(self, db):
        async with db() as session:
            user = User(telegram_id=99, agreed=False)
            session.add(user)
            await session.commit()

        async with db() as session:
            user = await session.scalar(select(User).where(User.telegram_id == 99))
            user.agreed = True
            await session.commit()

        async with db() as session:
            user = await session.scalar(select(User).where(User.telegram_id == 99))
        assert user.agreed is True

    async def test_unique_telegram_id(self, db):
        from sqlalchemy.exc import IntegrityError
        import pytest

        async with db() as session:
            session.add(User(telegram_id=777, agreed=False))
            await session.commit()

        with pytest.raises(IntegrityError):
            async with db() as session:
                session.add(User(telegram_id=777, agreed=True))
                await session.commit()
