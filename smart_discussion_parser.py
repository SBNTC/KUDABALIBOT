import asyncio
import json
import logging
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterEmpty
from config import config
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

KNOWLEDGE_DIR = Path("knowledge_base")

client_ai = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url
)

# Чаты для поиска
CHATS = [
    "balichat",
    "bali_chatik",
    "balichatsurfing", 
    "balidating",
    "balisurfer",
    "balibeauty",
    "balidances",
]

# Боты которых игнорируем
SKIP_BOTS = [
    "baliforumrubot",
    "kudabalibot",
    "bot",
]

# Транслит для поиска
TRANSLIT = {
    # Пляжи
    "amed": "амед", "balangan": "баланган", "bingin": "бингин",
    "dreamland": "дримленд", "jimbaran": "джимбаран", "kuta": "кута",
    "melasti": "меласти", "nusa dua": "нуса дуа", "padang": "паданг",
    "sanur": "санур", "seminyak": "семиньяк", "uluwatu": "улувату",
    "nyang nyang": "ньянг", "lovina": "ловина", "amed": "амед",
    "candidasa": "чандидаса", "berawa": "берава", "echo": "эхо",
    "keramas": "керамас", "medewi": "медеви", "geger": "гегер",
    "pandawa": "пандава", "karma": "карма", "suluban": "сулубан",
    "green bowl": "грин бол", "nusa penida": "пенида",
    
    # Водопады  
    "sekumpul": "секумпул", "gitgit": "гитгит", "tegenungan": "тегенунган",
    "tibumana": "тибумана", "kanto lampo": "канто", "leke leke": "леке",
    "aling aling": "алинг", "nungnung": "нунгнунг", "munduk": "мундук",
    
    # Храмы
    "tanah lot": "танах лот", "tirta empul": "тирта", "uluwatu": "улувату",
    "besakih": "бесаких", "lempuyang": "лемпуянг", "ulun danu": "улун дану",
    
    # Рестораны/кафе
    "finns": "финнс", "potato head": "потейто", "la brisa": "бриса",
    "milk madu": "милк маду", "crate": "крейт", "revolver": "револьвер",
    "shelter": "шелтер", "watercress": "вотеркресс", "kynd": "кайнд",
    "nook": "нук", "locavore": "локавор", "sisterfields": "систерфилдс",
}

# Ключевые слова для описания мест
PLACE_KEYWORDS = [
    "чистый", "грязный", "мусор", "людно", "пусто", "малолюдно",
    "волны", "течение", "купаться", "плавать", "серфить", "снорклинг",
    "красиво", "вид", "закат", "рассвет", "фото", "инстаграм",
    "вход", "платный", "бесплатно", "парковка", "лестница", "спуск",
    "песок", "камни", "кораллы", "рифы", "прозрачная", "мутная",
    "опасно", "безопасно", "флаги", "спасатели",
    "рекомендую", "советую", "понравилось", "разочаровал",
    "стоит", "не стоит", "лучше", "хуже",
    "были", "ездили", "ходили", "посетили",
    "еда", "кухня", "вкусно", "дорого", "дёшево", "цены",
    "атмосфера", "музыка", "сервис", "персонал",
    "?",  # Вопросы
]

AI_PROMPT = """Определи, является ли это сообщение РЕАЛЬНЫМ ОБСУЖДЕНИЕМ/ОТЗЫВОМ о месте "{place}".

РЕАЛЬНОЕ обсуждение — это когда человек:
- Делится личным опытом посещения места
- Спрашивает совет про это место (как там сейчас? стоит ли ехать?)
- Описывает состояние места (чисто, грязно, людно, волны, вода)
- Рекомендует или не рекомендует место

НЕ является обсуждением:
- Сообщение от бота со списком мест или ссылками
- Объявление об аренде жилья рядом с местом
- Реклама туров/услуг
- Просто упоминание места как локации без описания
- Общая справочная информация о месте

Сообщение:
"{text}"

Ответь ТОЛЬКО одним словом: YES или NO"""


async def check_is_discussion(place: str, text: str) -> bool:
    """Проверяет через AI — реальное обсуждение или нет"""
    try:
        response = await client_ai.chat.completions.create(
            model=config.deepseek_model,
            messages=[{"role": "user", "content": AI_PROMPT.format(place=place, text=text[:600])}],
            temperature=0,
            max_tokens=5
        )
        return "YES" in response.choices[0].message.content.strip().upper()
    except Exception as e:
        logging.error(f"AI error: {e}")
        return False


def get_search_query(name: str) -> str:
    """Получает поисковый запрос на русском"""
    name_lower = name.lower()
    
    for eng, rus in TRANSLIT.items():
        if eng in name_lower:
            # Добавляем тип места
            if "beach" in name_lower:
                return f"{rus} пляж"
            elif "waterfall" in name_lower:
                return f"{rus} водопад"
            elif "temple" in name_lower:
                return f"{rus} храм"
            else:
                return rus
    
    return name_lower


def is_bot_message(message) -> bool:
    """Проверяет что сообщение от бота"""
    if not message.sender:
        return True
    
    username = getattr(message.sender, 'username', '') or ''
    if username.lower() in SKIP_BOTS or username.lower().endswith('bot'):
        return True
    
    # Проверяем по тексту — если много ссылок baliforum.ru, это бот
    if message.text and message.text.count('baliforum.ru') >= 2:
        return True
    
    return False


def has_place_keywords(text: str) -> bool:
    """Быстрая проверка — есть ли ключевые слова описания места"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in PLACE_KEYWORDS)


async def search_discussions_for_place(client, place_name: str, limit: int = 3) -> list:
    """Ищет обсуждения места в чатах"""
    query = get_search_query(place_name)
    logging.info(f"  🔍 Поиск: {place_name} -> '{query}'")
    
    all_messages = []
    
    for chat in CHATS:
        try:
            async for message in client.iter_messages(chat, search=query, limit=20):
                if not message.text or len(message.text) < 30:
                    continue
                
                # Пропускаем ботов
                if is_bot_message(message):
                    continue
                
                # Быстрая проверка ключевых слов
                if not has_place_keywords(message.text):
                    continue
                
                # Формируем ссылку
                if hasattr(message.chat, 'username') and message.chat.username:
                    link = f"https://t.me/{message.chat.username}/{message.id}"
                else:
                    link = f"https://t.me/c/{message.chat.id}/{message.id}"
                
                all_messages.append({
                    'text': message.text[:600],
                    'link': link,
                    'chat': chat,
                })
                
        except Exception as e:
            logging.error(f"    ❌ {chat}: {e}")
    
    logging.info(f"    Найдено {len(all_messages)} кандидатов")
    
    # Фильтруем через AI
    good = []
    for msg in all_messages[:15]:  # Проверяем первые 15
        is_good = await check_is_discussion(place_name, msg['text'])
        if is_good:
            good.append({'link': msg['link'], 'chat': msg['chat']})
            logging.info(f"    ✅ {msg['text'][:50]}...")
            if len(good) >= limit:
                break
        await asyncio.sleep(0.2)
    
    return good


async def parse_all_places():
    """Парсит обсуждения для всех мест"""
    client = TelegramClient('anon_session', int(config.telegram_api_id), config.telegram_api_hash)
    await client.start()
    
    total_found = 0
    
    for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
        logging.info(f"\n📁 {json_file.stem}")
        
        with open(json_file) as f:
            places = json.load(f)
        
        updated = False
        for place in places:
            name = place.get("name", "")
            if not name:
                continue
            
            # Пропускаем если уже есть 3+ обсуждения
            if len(place.get("mentions", [])) >= 3:
                continue
            
            discussions = await search_discussions_for_place(client, name, limit=3)
            
            if discussions:
                # Добавляем к существующим
                existing = place.get("mentions", [])
                existing_links = {m['link'] for m in existing}
                
                for d in discussions:
                    if d['link'] not in existing_links:
                        existing.append(d)
                
                place["mentions"] = existing[:5]  # Макс 5
                updated = True
                total_found += len(discussions)
            
            await asyncio.sleep(1)  # Пауза между местами
        
        if updated:
            with open(json_file, 'w') as f:
                json.dump(places, f, ensure_ascii=False, indent=2)
    
    await client.disconnect()
    logging.info(f"\n✅ Всего найдено: {total_found} обсуждений")


if __name__ == "__main__":
    asyncio.run(parse_all_places())
