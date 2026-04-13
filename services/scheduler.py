"""
Планировщик задач:

  - 06:00 Asia/Makassar — парсинг baliforum.ru (site_parser)
  - 08:00 и 20:00       — сканирование Telegram-чатов (collector)
  - После каждого сбора — dedup → analyzer(pending -> review)
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.analyzer import run_batch_analysis, cleanup_old_events
from services.site_parser import run_site_parser
from services.collector import scheduled_chat_scan
from services.dedup import run_full_dedup


logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Makassar")


async def _dedup_and_analyze(origin: str) -> None:
    """Сквозной прогон: cleanup → dedup → batch analyze."""
    logger.info(f"🧮 [{origin}] dedup + analyze...")
    try:
        await cleanup_old_events()
    except Exception as e:
        logger.error(f"cleanup_old_events: {e}")

    try:
        await run_full_dedup()
    except Exception as e:
        logger.error(f"dedup: {e}")

    try:
        # Проходим анализом несколько раз, пока pending не кончится
        while True:
            result = await run_batch_analysis()  # -> review (не approved!)
            logger.info(f"📊 {result}")
            if "Нет новых" in result or "📭" in result:
                break
    except Exception as e:
        logger.error(f"analyzer: {e}")


async def scheduled_site_parse() -> None:
    logger.info(f"⏰ [{datetime.now(timezone.utc)}] Парсинг baliforum.ru...")
    try:
        saved = await run_site_parser()
        logger.info(f"🌐 site_parser сохранил: {saved}")
    except Exception as e:
        logger.error(f"❌ site_parser: {e}")

    await _dedup_and_analyze("site_parser")


async def scheduled_chat_parse() -> None:
    logger.info(f"⏰ [{datetime.now(timezone.utc)}] Сканирование Telegram-чатов...")
    try:
        saved = await scheduled_chat_scan()
        logger.info(f"📡 collector сохранил: {saved}")
    except Exception as e:
        logger.error(f"❌ collector: {e}")

    await _dedup_and_analyze("collector")


async def retry_stale_pending() -> None:
    """Повторная обработка pending-событий старше 1 часа."""
    from sqlalchemy import select, update
    from database.models import ScrapedEvent
    from database.session import AsyncSessionMaker

    logger.info("🔄 Retry stale pending events...")
    try:
        result = await run_batch_analysis()
        logger.info(f"📊 Retry pending: {result}")
    except Exception as e:
        logger.error(f"retry_stale_pending: {e}")


async def setup_scheduler() -> None:  # noqa: F401 — публичный API
    # 1 раз в день — baliforum.ru
    scheduler.add_job(
        scheduled_site_parse,
        trigger=CronTrigger(hour=6, minute=0),
        id="site_parser_daily",
        replace_existing=True,
    )

    # 2 раза в день — Telegram-чаты
    scheduler.add_job(
        scheduled_chat_parse,
        trigger=CronTrigger(hour="8,20", minute=0),
        id="chat_scan_twice_daily",
        replace_existing=True,
    )

    # Раз в день — повторная обработка застрявших pending
    scheduler.add_job(
        retry_stale_pending,
        trigger=CronTrigger(hour=14, minute=0),
        id="retry_pending_daily",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "📅 Планировщик запущен: "
        "site_parser=06:00, chat_scan=08:00/20:00, retry_pending=14:00 (Asia/Makassar)"
    )
