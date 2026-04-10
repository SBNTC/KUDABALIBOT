import json
import logging
import time
from pathlib import Path
from openai import AsyncOpenAI
from config import config
from data.statuses import EventStatus
from services.reviews_analyzer import get_place_reviews

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url,
)

_KNOWLEDGE_TTL = 3600.0  # перезагружаем базу знаний раз в час
_knowledge_cache: dict = {}
_knowledge_loaded_at: float = 0.0


def _load_knowledge_from_disk() -> dict:
    knowledge: dict = {}
    knowledge_dir = Path("knowledge_base")
    for json_file in knowledge_dir.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                knowledge[json_file.stem] = json.load(f)
        except Exception:
            pass
    return knowledge


def _get_knowledge() -> dict:
    global _knowledge_cache, _knowledge_loaded_at
    if time.monotonic() - _knowledge_loaded_at > _KNOWLEDGE_TTL:
        _knowledge_cache = _load_knowledge_from_disk()
        _knowledge_loaded_at = time.monotonic()
        logging.debug(f"ai_assistant: reloaded knowledge base ({len(_knowledge_cache)} categories)")
    return _knowledge_cache

SYSTEM_PROMPT = """Ты — дружелюбный гид по Бали. Помогаешь с вопросами о:
- Ресторанах, кафе, барах
- Пляжах и серф-спотах  
- Коворкингах для удалённой работы
- Храмах и достопримечательностях
- Водопадах и активностях
- Районах для жизни
- Визах, транспорте, медицине

Отвечай кратко и по делу. Используй эмодзи. Если есть отзывы реальных людей — цитируй их.

БАЗА ЗНАНИЙ:
{knowledge}

ОТЗЫВЫ ИЗ ЧАТОВ:
{reviews}

АФИША СОБЫТИЙ (ближайшие мероприятия):
{events}
"""


async def get_upcoming_events(query: str) -> str:  # noqa: ARG001 — query reserved for future date filtering
    """Загружает ближайшие актуальные события из афиши."""
    from sqlalchemy import select, or_
    from datetime import date
    from database.models import ScrapedEvent
    from database.session import AsyncSessionMaker

    today = date.today()
    async with AsyncSessionMaker() as session:
        q = select(ScrapedEvent).where(
            ScrapedEvent.status == EventStatus.APPROVED,
            ScrapedEvent.category.notin_(["Spam", "Unknown"]),
            or_(
                ScrapedEvent.event_date >= today,
                ScrapedEvent.event_date.is_(None)  # Регулярные события
            )
        ).order_by(ScrapedEvent.event_date.asc().nulls_last()).limit(30)
        
        result = await session.execute(q)
        events = result.scalars().all()
    
    if not events:
        return "Нет актуальных событий"
    
    lines = []
    for e in events:
        date_str = e.event_date.strftime("%d.%m") if e.event_date else "регулярно"
        cat = e.category or ""
        summary = e.summary or e.raw_text[:100] if e.raw_text else "Без описания"
        link = e.link or ""
        lines.append(f"[{date_str}] {cat}: {summary} | {link}")
    
    return "\n".join(lines)

async def get_ai_response(user_message: str, chat_history: list = None) -> str:
    """Получает ответ от AI с учётом базы знаний и афиши."""
    relevant_knowledge = find_relevant_knowledge(user_message)
    
    # Ищем события из афиши
    events_text = await get_upcoming_events(user_message)
    
    # Ищем отзывы
    reviews_text = await find_relevant_reviews(user_message)
    
    system = SYSTEM_PROMPT.format(
        knowledge=json.dumps(relevant_knowledge, ensure_ascii=False)[:4000],
        reviews=reviews_text[:2000],
        events=events_text[:3000]
    )
    
    messages = [{"role": "system", "content": system}]
    
    # Добавляем историю (последние 6 сообщений)
    if chat_history:
        messages.extend(chat_history[-6:])
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = await client.chat.completions.create(
            model=config.deepseek_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        answer = response.choices[0].message.content or "Не могу ответить 😔"
        # Убираем markdown форматирование
        answer = answer.replace("**", "").replace("*", "")
        return answer
    except Exception as e:
        logging.error(f"AI error: {e}")
        return "Произошла ошибка. Попробуй ещё раз 🔄"


_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "restaurants": ["ресторан", "поесть", "еда", "кухня", "ужин", "обед", "завтрак"],
    "cafes": ["кафе", "кофе", "бранч", "завтрак"],
    "beaches": ["пляж", "море", "купаться", "песок"],
    "coworkings": ["коворкинг", "работать", "wifi", "ноутбук", "удалёнка"],
    "temples": ["храм", "temple", "достопримечательност"],
    "waterfalls": ["водопад", "waterfall"],
    "surf_spots": ["серф", "surf", "волн"],
    "yoga": ["йога", "yoga", "медитац"],
    "spas": ["спа", "массаж", "spa"],
    "clubs": ["клуб", "club", "вечеринк", "тусовк", "ночн"],
}


def find_relevant_knowledge(query: str) -> list:
    """Ищет релевантные места в базе знаний."""
    knowledge = _get_knowledge()
    query_lower = query.lower()

    relevant_categories = [
        cat for cat, keywords in _CATEGORY_KEYWORDS.items()
        if any(kw in query_lower for kw in keywords)
    ] or list(knowledge.keys())

    results: list = []
    for cat in relevant_categories:
        results.extend(knowledge.get(cat, [])[:10])

    return results[:20]


async def find_relevant_reviews(query: str) -> str:
    """Ищет релевантные отзывы."""
    knowledge = _get_knowledge()
    query_lower = query.lower()
    reviews_text = ""

    for items in knowledge.values():
        for item in items:
            name = item.get("name", "").lower()
            if name and len(name) > 3 and name in query_lower:
                reviews = await get_place_reviews(item["name"], limit=3)
                if reviews:
                    reviews_text += f"\n📍 {item['name']}:\n"
                    for r in reviews:
                        icon = "👍" if r["sentiment"] == "positive" else "👎" if r["sentiment"] == "negative" else "💬"
                        reviews_text += f"  {icon} @{r['username']}: {r['text'][:100]}\n"

    return reviews_text
