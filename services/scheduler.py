"""Планировщик задач (только analyzer, БЕЗ collector)"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from services.analyzer import run_batch_analysis
from config import config
from datetime import datetime

scheduler = AsyncIOScheduler(timezone="Asia/Makassar")

async def scheduled_analysis():
    """Периодический анализ постов (collector работает отдельно)"""
    logging.info(f"⏰ [{datetime.now()}] Автоанализ...")
    
    try:
        while True:
            result = await run_batch_analysis()
            logging.info(f"📊 {result}")
            if "Нет новых" in result or "📭" in result:
                break
    except Exception as e:
        logging.error(f"❌ Analyzer: {e}")

async def setup_scheduler():
    """Настройка планировщика (ТОЛЬКО analyzer)"""
    scheduler.add_job(
        scheduled_analysis,
        trigger=IntervalTrigger(hours=config.scan_interval_hours),
        id="auto_analyze",
        replace_existing=True
    )
    
    scheduler.start()
    logging.info(f"📅 Планировщик: каждые {config.scan_interval_hours}ч")
