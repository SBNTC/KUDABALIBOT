import json
import logging
import re
from datetime import datetime, timezone
from sqlalchemy import select
from openai import AsyncOpenAI
from database.models import AsyncSessionMaker, PlaceReview
from config import config
from pathlib import Path

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url
)

# Загружаем названия мест из базы знаний
def load_place_names() -> list[str]:
    places = []
    knowledge_dir = Path("knowledge_base")
    for json_file in knowledge_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
                for item in data:
                    if item.get("name"):
                        places.append(item["name"])
        except:
            pass
    return places

PLACE_NAMES = load_place_names()

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


async def analyze_message_for_reviews(
    text: str,
    chat_title: str,
    username: str,
    link: str,
    message_date: datetime
) -> int:
    """Анализирует сообщение и сохраняет найденные отзывы"""
    
    if len(text) < 20:
        return 0
    
    # Быстрая проверка — есть ли вообще названия мест
    text_lower = text.lower()
    has_potential_place = any(
        place.lower() in text_lower 
        for place in PLACE_NAMES[:100]  # Проверяем первые 100
    )
    
    # Или ключевые слова отзывов
    review_keywords = ['рекомендую', 'советую', 'понравил', 'не понравил', 'топ', 'огонь', 'отстой', 'был в', 'были в', 'ходили', 'лучший', 'худший']
    has_review_keyword = any(kw in text_lower for kw in review_keywords)
    
    if not has_potential_place and not has_review_keyword:
        return 0
    
    try:
        # Отправляем на анализ
        prompt = REVIEW_PROMPT.format(
            places=", ".join(PLACE_NAMES[:200]),  # Топ 200 мест
            text=text[:1000]
        )
        
        response = await client.chat.completions.create(
            model=config.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        raw = response.choices[0].message.content or ""
        
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
    """Ищет совпадение в базе знаний"""
    mentioned_lower = mentioned.lower().strip()
    
    # Точное совпадение
    for place in PLACE_NAMES:
        if place.lower() == mentioned_lower:
            return place
    
    # Частичное совпадение
    for place in PLACE_NAMES:
        if mentioned_lower in place.lower() or place.lower() in mentioned_lower:
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
