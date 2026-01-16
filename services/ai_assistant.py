import json
import logging
from pathlib import Path
from openai import AsyncOpenAI
from config import config
from services.reviews_analyzer import get_place_reviews

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url
)

# Загружаем базу знаний
def load_knowledge_base() -> dict:
    knowledge = {}
    knowledge_dir = Path("knowledge_base")
    for json_file in knowledge_dir.glob("*.json"):
        try:
            with open(json_file, encoding='utf-8') as f:
                knowledge[json_file.stem] = json.load(f)
        except:
            pass
    return knowledge

KNOWLEDGE = load_knowledge_base()

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


async def get_upcoming_events(query: str) -> str:
    """Загружает ближайшие события из афиши"""
    from sqlalchemy import select, or_
    from datetime import date, timedelta
    from database.models import AsyncSessionMaker, ScrapedEvent
    
    today = date.today()
    week_later = today + timedelta(days=7)
    
    # Извлекаем дату из запроса если есть
    import re
    date_match = re.search(r'(\d{1,2})\s*(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)', query.lower())
    
    async with AsyncSessionMaker() as session:
        q = select(ScrapedEvent).where(
            ScrapedEvent.status == "approved",
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
    """Получает ответ от AI с учётом базы знаний и афиши"""
    
    # Ищем релевантные места в базе
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


def find_relevant_knowledge(query: str) -> list:
    """Ищет релевантные места в базе знаний"""
    query_lower = query.lower()
    results = []
    
    # Ключевые слова для категорий
    category_keywords = {
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
    
    # Определяем релевантные категории
    relevant_categories = []
    for cat, keywords in category_keywords.items():
        if any(kw in query_lower for kw in keywords):
            relevant_categories.append(cat)
    
    # Если категория не определена — ищем по всем
    if not relevant_categories:
        relevant_categories = list(KNOWLEDGE.keys())
    
    # Собираем данные
    for cat in relevant_categories:
        if cat in KNOWLEDGE:
            for item in KNOWLEDGE[cat][:10]:  # Макс 10 из категории
                results.append(item)
    
    return results[:20]  # Макс 20 результатов


async def find_relevant_reviews(query: str) -> str:
    """Ищет релевантные отзывы"""
    query_lower = query.lower()
    reviews_text = ""
    
    # Ищем упоминания мест в запросе
    for cat, items in KNOWLEDGE.items():
        for item in items:
            name = item.get("name", "").lower()
            if name and len(name) > 3 and name in query_lower:
                reviews = await get_place_reviews(item["name"], limit=3)
                if reviews:
                    reviews_text += f"\n📍 {item['name']}:\n"
                    for r in reviews:
                        sentiment_icon = "👍" if r["sentiment"] == "positive" else "👎" if r["sentiment"] == "negative" else "💬"
                        reviews_text += f"  {sentiment_icon} @{r['username']}: {r['text'][:100]}\n"
    
    return reviews_text
