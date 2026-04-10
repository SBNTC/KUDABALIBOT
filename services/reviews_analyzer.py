import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from openai import AsyncOpenAI
from database.models import PlaceReview
from config import config
from database.session import AsyncSessionMaker

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url,
)

# Semaphore: не более 2 одновременных API-вызовов для review-анализа
_review_semaphore = asyncio.Semaphore(2)

# TTL-кэш названий мест (обновляется раз в час)
_place_names_cache: list[str] = []
_place_names_loaded_at: float = 0.0
_PLACE_NAMES_TTL = 3600.0


def _load_place_names_from_disk() -> list[str]:
    places: list[str] = []
    knowledge_dir = Path("knowledge_base")
    for json_file in knowledge_dir.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if item.get("name"):
                        places.append(item["name"])
        except Exception:
            pass
    return places


def _get_place_names() -> list[str]:
    global _place_names_cache, _place_names_loaded_at
    if time.monotonic() - _place_names_loaded_at > _PLACE_NAMES_TTL:
        _place_names_cache = _load_place_names_from_disk()
        _place_names_loaded_at = time.monotonic()
        logging.debug(f"reviews_analyzer: reloaded {len(_place_names_cache)} place names")
    return _place_names_cache

REVIEW_PROMPT = """Проанализируй сообщение из чата про Бали. Найди упоминания конкретных мест (рестораны, кафе, пляжи, отели, клубы, спа).

Для каждого упомянутого места определи:
1. mentioned_name — как именно написано в тексте
2. sentiment — тональность: positive / negative / neutral
3. relevant_text — только та часть сообщения которая относится к этому месту (1-2 предложения)

Известные места: {places}

Сообщение:
{text}

Ответ строго в JSON:
[{{"mentioned_name": "...", "sentiment": "...", "relevant_text": "..."}}]

Если мест не упомянуто — верни пустой массив []
"""


_REVIEW_KEYWORDS = frozenset([
    'рекомендую', 'советую', 'понравил', 'не понравил', 'топ', 'огонь',
    'отстой', 'был в', 'были в', 'ходили', 'лучший', 'худший',
])


async def _call_deepseek_review(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            async with _review_semaphore:
                response = await client.chat.completions.create(
                    model=config.deepseek_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1000,
                )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logging.warning(f"DeepSeek review retry {attempt + 1}/{retries} in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                logging.error(f"DeepSeek review failed after {retries} attempts: {e}")
    return ""


async def analyze_message_for_reviews(
    text: str,
    chat_title: str,
    username: str,
    link: str,
    message_date: datetime,
) -> int:
    """Анализирует сообщение и сохраняет найденные отзывы."""
    if len(text) < 20:
        return 0

    place_names = _get_place_names()
    text_lower = text.lower()

    # Быстрая проверка — есть ли названия мест или маркеры отзыва
    has_potential_place = any(place.lower() in text_lower for place in place_names[:150])
    has_review_keyword = any(kw in text_lower for kw in _REVIEW_KEYWORDS)

    if not has_potential_place and not has_review_keyword:
        return 0

    try:
        prompt = REVIEW_PROMPT.format(
            places=", ".join(place_names[:200]),
            text=text[:1000],
        )

        raw = await _call_deepseek_review(prompt)
        
        # Парсим JSON
        match = re.search(r'\[.*\]', raw.replace('\n', ' '), re.DOTALL)
        if not match:
            return 0
        
        reviews = json.loads(match.group(0))
        if not reviews:
            return 0
        
        # Сохраняем в БД
        saved = 0
        async with AsyncSessionMaker() as session:
            for r in reviews:
                mentioned = r.get("mentioned_name", "")
                if not mentioned:
                    continue
                
                # Нормализуем название (ищем в базе)
                place_name = find_matching_place(mentioned)
                if not place_name:
                    place_name = mentioned  # Сохраняем как есть
                
                review = PlaceReview(
                    place_name=place_name,
                    mentioned_name=mentioned,
                    chat_title=chat_title,
                    username=username or "anonymous",
                    message_text=r.get("relevant_text", text[:200]),
                    sentiment=r.get("sentiment", "neutral"),
                    link=link,
                    message_date=message_date
                )
                session.add(review)
                saved += 1
            
            await session.commit()
        
        if saved:
            logging.info(f"💬 Сохранено {saved} отзывов из {chat_title}")
        
        return saved
        
    except Exception as e:
        logging.error(f"Review analyze error: {e}")
        return 0


def find_matching_place(mentioned: str) -> str | None:
    """Ищет совпадение в базе знаний."""
    place_names = _get_place_names()
    mentioned_lower = mentioned.lower().strip()
    if not mentioned_lower:
        return None

    for place in place_names:
        if place.lower() == mentioned_lower:
            return place

    for place in place_names:
        pl = place.lower()
        if mentioned_lower in pl or pl in mentioned_lower:
            return place

    return None


async def get_place_reviews(place_name: str, limit: int = 5) -> list[dict]:
    """Получает последние отзывы о месте"""
    async with AsyncSessionMaker() as session:
        result = await session.execute(
            select(PlaceReview)
            .where(PlaceReview.place_name.ilike(f"%{place_name}%"))
            .order_by(PlaceReview.message_date.desc())
            .limit(limit)
        )
        reviews = result.scalars().all()
        
        return [
            {
                "text": r.message_text,
                "sentiment": r.sentiment,
                "username": r.username,
                "chat": r.chat_title,
                "date": r.message_date,
                "link": r.link
            }
            for r in reviews
        ]
