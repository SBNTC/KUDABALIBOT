import asyncio
import json
import logging
import re
from datetime import date
from sqlalchemy import select, update, delete
from openai import AsyncOpenAI
from database.models import ScrapedEvent
from data.statuses import EventStatus
from config import config
from database.session import AsyncSessionMaker

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url
)

BATCH_SIZE = 20

PROMPT = """Ты — редактор афиши Бали. Классифицируй сообщения.

## ВАЖНО: ФИЛЬТРАЦИЯ СУПЕР-МЯГКАЯ
Пропускай ВСЁ, что хотя бы ОТДАЛЁННО похоже на событие/активность/встречу.
Лучше пропустить лишнее на ручную модерацию, чем потерять событие.
Если сомневаешься — НЕ Spam.

## КАТЕГОРИИ:
- Free: бесплатно, donation, донейшн, вход свободный, открытый урок
- Paid: платно, есть цена, билеты
- Networking: бизнес-встречи, нетворкинги, завтраки, speaking-клубы
- Party: вечеринки, DJ, концерты, тусовки, ecstatic dance

## Spam — ТОЛЬКО для явного мусора:
- прямая реклама товаров (iPhone, байки, одежда)
- аренда/сдача/поиск жилья БЕЗ события
- продажа/покупка вещей, обмен валют, визаран
- бытовые вопросы без контекста события ("кто знает врача", "где купить")
- вакансии, резюме, поиск работы
ВСЁ остальное — НЕ Spam. Даже короткие анонсы, даже без даты, даже странные.

## summary: короткий заголовок ДО 60 символов, по-русски.
## event_date: YYYY-MM-DD если дата явно указана, иначе null.

## ОТВЕТ (строго JSON-массив, ничего больше):
[{"id": 123, "category": "Free", "summary": "Йога в Убуде, 18:00", "event_date": "2025-12-28"}]

Данные:
DATA_PLACEHOLDER
"""


async def call_deepseek(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model=config.deepseek_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=3000,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logging.warning(f"DeepSeek attempt {attempt + 1}/{retries} failed, retry in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                logging.error(f"DeepSeek failed after {retries} attempts: {e}")
    return ""


def parse_event_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except:
        return None


async def cleanup_old_events():
    """Удаление прошедших событий"""
    today = date.today()
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            delete(ScrapedEvent)
            .where(ScrapedEvent.event_date < today)
            .where(ScrapedEvent.is_recurring == False)
            .where(ScrapedEvent.event_date.isnot(None))
        )
        await session.commit()
        if result.rowcount:
            logging.info(f"🗑 Удалено прошедших: {result.rowcount}")


async def run_batch_analysis(auto_approve: bool = False) -> str:
    """
    Анализ pending событий.
    auto_approve=True -> сразу в approved (первичный сбор)
    auto_approve=False -> в review (на модерацию)
    """
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(ScrapedEvent).where(ScrapedEvent.status == EventStatus.PENDING)
        )
        batch = result.scalars().all()
        
        if not batch:
            return "📭 Нет новых сообщений."

        total = len(batch)
        logging.info(f"📊 Pending: {total}")
        
        current_date = date.today().isoformat()
        total_processed = 0
        total_spam = 0
        total_errors = 0

        target_status = EventStatus.APPROVED if auto_approve else EventStatus.REVIEW

        for i in range(0, total, BATCH_SIZE):
            chunk = batch[i:i+BATCH_SIZE]
            
            data_for_ai = []
            for e in chunk:
                posted = e.created_at.strftime("%Y-%m-%d") if e.created_at else current_date
                text = re.sub(r'\s+', ' ', (e.raw_text or "")[:500]).strip()
                data_for_ai.append({"id": e.id, "text": text, "posted": posted})

            try:
                prompt = PROMPT.replace("DATA_PLACEHOLDER", json.dumps(data_for_ai, ensure_ascii=False))
                raw = await call_deepseek(prompt)
                
                match = re.search(r'\[.*\]', raw.replace('\n', ' '), re.DOTALL)
                if not match:
                    logging.warning("No JSON in response")
                    continue
                
                ai_results = json.loads(match.group(0))
                results_map = {item.get("id"): item for item in ai_results}

                for e in chunk:
                    res = results_map.get(e.id)
                    
                    if not res or res.get("category") == "Spam":
                        await session.execute(
                            update(ScrapedEvent)
                            .where(ScrapedEvent.id == e.id)
                            .values(status=EventStatus.REJECTED, category="Spam")
                        )
                        total_spam += 1
                    else:
                        await session.execute(
                            update(ScrapedEvent)
                            .where(ScrapedEvent.id == e.id)
                            .values(
                                status=target_status,
                                category=res.get("category", "Unknown"),
                                summary=res.get("summary", ""),
                                event_date=parse_event_date(res.get("event_date"))
                            )
                        )
                        total_processed += 1
                
                await session.commit()
                
            except Exception as e:
                logging.error(f"Chunk error: {e}")
                total_errors += len(chunk)

        status_word = "Одобрено" if auto_approve else "На модерацию"
        return f"✅ {status_word}: {total_processed}, Спам: {total_spam}, Ошибок: {total_errors}"


async def analyze_realtime_event(event_id: int) -> None:
    """Анализ одного события в реальном времени -> review"""
    async with AsyncSessionMaker() as session:
        ev = await session.get(ScrapedEvent, event_id)
        if not ev or ev.status != EventStatus.PENDING:
            return
        
        text = re.sub(r'\s+', ' ', (ev.raw_text or "")[:500]).strip()
        posted = ev.created_at.strftime("%Y-%m-%d") if ev.created_at else date.today().isoformat()
        
        data = [{"id": ev.id, "text": text, "posted": posted}]
        prompt = PROMPT.replace("DATA_PLACEHOLDER", json.dumps(data, ensure_ascii=False))
        
        try:
            raw = await call_deepseek(prompt)
            match = re.search(r'\[.*\]', raw.replace('\n', ' '), re.DOTALL)
            if not match:
                return
            
            ai_results = json.loads(match.group(0))
            if not ai_results:
                return
            
            res = ai_results[0]
            
            if res.get("category") == "Spam":
                ev.status = EventStatus.REJECTED
                ev.category = "Spam"
            else:
                ev.status = EventStatus.REVIEW
                ev.category = res.get("category", "Unknown")
                ev.summary = res.get("summary", "")
                ev.event_date = parse_event_date(res.get("event_date"))
            
            await session.commit()
            logging.info(f"📊 Realtime: {ev.id} -> {ev.status}")
            
        except Exception as e:
            logging.error(f"Realtime analyze error: {e}")
