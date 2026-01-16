import json
import re
import logging
from pathlib import Path
from sqlalchemy import select, func
from database.models import AsyncSessionMaker, ScrapedEvent

KNOWLEDGE_DIR = Path("knowledge_base")

TRANSLIT_MAP = {
    'dreamland': ['дримленд', 'дримлэнд'], 'balangan': ['балангане', 'баланган'],
    'bingin': ['бингин'], 'melasti': ['меласти'], 'padang': ['паданг'],
    'nyang nyang': ['ньянг ньянг', 'нянг нянг'], 'uluwatu': ['улувату'],
    'seminyak': ['семиньяк'], 'canggu': ['чангу', 'чанггу'], 'ubud': ['убуд'],
    'sanur': ['санур'], 'jimbaran': ['джимбаран', 'джимбарана'],
    'kuta': ['кута', 'куте'], 'nusa dua': ['нуса дуа'],
    'tanah lot': ['танах лот'], 'tirta empul': ['тирта эмпул'],
    'tegallalang': ['тегаллаланг', 'тегалаланг'], 'ubud palace': ['убуд палас'],
    'monkey forest': ['манки форест', 'лес обезьян'],
    'sekumpul': ['секумпул'], 'tegenungan': ['тегенунган'],
    'gitgit': ['гитгит'], 'tibumana': ['тибумана'],
    'leke leke': ['леке леке'], 'kanto lampo': ['канто лампо'],
    'finns': ['финнс'], 'potato head': ['потейто хед', 'потато хед'],
    'la brisa': ['ла бриса'], 'motel mexicola': ['мотель мексикола'],
    'milk madu': ['милк маду'], 'crate cafe': ['крейт кафе'],
    'sisterfields': ['систерфилдс'], 'revolver': ['револьвер'],
    'shelter': ['шелтер'], 'la lucciola': ['ла лучиола'],
}

# Слова-маркеры что это НЕ обсуждение, а объявление
SKIP_MARKERS = [
    'сдается', 'сдаётся', 'аренда', 'продается', 'продаётся', 
    'млн в месяц', 'в месяц', '/мес', '$ в месяц', 'usd в месяц',
    'спальни', 'спален', 'bedroom', 'ванные', 'ванных',
    'апартаменты', 'вилла сдам', 'дом сдам', 'квартира',
    '#реклама', '#аренда', '#продажа', 'пишите в лс',
    'скидка за', 'бонусом:', 'электричество /',
]

# Слова-маркеры что это ОБСУЖДЕНИЕ
DISCUSSION_MARKERS = [
    'как там', 'что там', 'как сейчас', 'подскажите', 'посоветуйте',
    'кто был', 'кто ездил', 'были на', 'ездили на', 'ходили в',
    'понравилось', 'не понравилось', 'рекомендую', 'не рекомендую',
    'советую', 'не советую', 'топ', 'огонь', 'отстой', 'фигня',
    'стоит ли', 'стоит ехать', 'как добраться', 'сколько стоит вход',
    'с мусором', 'чистый', 'грязный', 'много людей', 'мало людей',
    'волны', 'течение', 'опасно', 'безопасно',
    '?',  # вопросы часто = обсуждения
]


def get_search_variants(name: str) -> list[str]:
    """Генерирует варианты поиска на русском"""
    variants = []
    name_lower = name.lower()
    
    # Ищем в транслит-мапе
    for eng, rus_list in TRANSLIT_MAP.items():
        if eng in name_lower:
            variants.extend(rus_list)
    
    # Если ничего не нашли — пробуем простую транслитерацию
    if not variants:
        # Базовый транслит
        simple = name_lower
        for eng, rus_list in TRANSLIT_MAP.items():
            if eng in simple:
                simple = simple.replace(eng, rus_list[0])
        if simple != name_lower:
            variants.append(simple)
    
    return [v for v in variants if len(v) >= 4]


def is_discussion(text: str) -> bool:
    """Проверяет что текст — обсуждение, а не объявление"""
    text_lower = text.lower()
    
    # Пропускаем объявления
    for marker in SKIP_MARKERS:
        if marker in text_lower:
            return False
    
    # Ищем маркеры обсуждения
    for marker in DISCUSSION_MARKERS:
        if marker in text_lower:
            return True
    
    # Если короткое сообщение без маркеров объявления — возможно обсуждение
    if len(text) < 200:
        return True
    
    return False


async def find_mentions_for_place(place_name: str, limit: int = 3) -> list[dict]:
    """Ищет обсуждения места в чатах"""
    variants = get_search_variants(place_name)
    if not variants:
        return []
    
    mentions = []
    
    async with AsyncSessionMaker() as session:
        for variant in variants:
            result = await session.execute(
                select(ScrapedEvent)
                .where(ScrapedEvent.raw_text.ilike(f"%{variant}%"))
                .where(ScrapedEvent.chat_title != "user_suggest")
                .where(ScrapedEvent.chat_title != "baliforum.ru")
                .order_by(ScrapedEvent.created_at.desc())
                .limit(50)  # Берём больше, потом фильтруем
            )
            
            for event in result.scalars():
                if not event.link or not event.raw_text:
                    continue
                
                # Фильтруем — только обсуждения
                if not is_discussion(event.raw_text):
                    continue
                
                # Проверяем дубли
                if any(m['link'] == event.link for m in mentions):
                    continue
                
                mentions.append({
                    'chat': event.chat_title[:25],
                    'link': event.link,
                })
                
                if len(mentions) >= limit:
                    break
            
            if len(mentions) >= limit:
                break
    
    return mentions


async def update_places_with_mentions():
    """Обновляет места ссылками на обсуждения"""
    from database.models import init_db
    await init_db()
    
    logging.info("🔍 Поиск обсуждений мест в чатах...")
    
    total_found = 0
    
    for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                places = json.load(f)
        except Exception as e:
            logging.error(f"❌ {json_file.name}: {e}")
            continue
        
        updated = False
        for place in places:
            name = place.get("name", "")
            if not name:
                continue
            
            mentions = await find_mentions_for_place(name, limit=3)
            
            if mentions:
                place["mentions"] = mentions
                updated = True
                total_found += len(mentions)
            else:
                place.pop("mentions", None)
        
        if updated:
            tmp_file = json_file.with_suffix('.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(places, f, ensure_ascii=False, indent=2)
            tmp_file.rename(json_file)
            
            count = sum(1 for p in places if p.get("mentions"))
            logging.info(f"  {json_file.stem}: {count} мест с обсуждениями")
    
    logging.info(f"✅ Найдено {total_found} обсуждений")
    return total_found


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    asyncio.run(update_places_with_mentions())
