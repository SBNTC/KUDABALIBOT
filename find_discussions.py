import json
import asyncio
import logging
from pathlib import Path
from sqlalchemy import select
from database.models import AsyncSessionMaker, ScrapedEvent, init_db
from openai import AsyncOpenAI
from config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

KNOWLEDGE_DIR = Path("knowledge_base")

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url
)

# Все варианты названий мест (рус + англ)
PLACE_VARIANTS = {
    # Пляжи
    'dreamland': ['дримленд', 'дримлэнд', 'dreamland'],
    'balangan': ['баланган', 'балангане', 'balangan'],
    'bingin': ['бингин', 'bingin'],
    'padang padang': ['паданг паданг', 'padang padang', 'паданг'],
    'melasti': ['меласти', 'melasti'],
    'nyang nyang': ['ньянг ньянг', 'нянг нянг', 'nyang'],
    'uluwatu': ['улувату', 'uluwatu'],
    'jimbaran': ['джимбаран', 'джимбарана', 'jimbaran'],
    'sanur': ['санур', 'сануре', 'sanur'],
    'nusa dua': ['нуса дуа', 'nusa dua'],
    'kuta beach': ['кута пляж', 'kuta beach', 'куте'],
    'seminyak beach': ['семиньяк пляж', 'seminyak'],
    'echo beach': ['эхо бич', 'echo beach'],
    'berawa': ['берава', 'berawa'],
    'batu bolong': ['бату болонг', 'batu bolong'],
    
    # Водопады
    'sekumpul': ['секумпул', 'sekumpul'],
    'tegenungan': ['тегенунган', 'tegenungan'],
    'gitgit': ['гитгит', 'gitgit'],
    'tibumana': ['тибумана', 'tibumana'],
    'leke leke': ['леке леке', 'leke leke'],
    'kanto lampo': ['канто лампо', 'kanto lampo'],
    'aling aling': ['алинг алинг', 'aling aling'],
    'nungnung': ['нунгнунг', 'nungnung'],
    'banyumala': ['баньюмала', 'banyumala'],
    
    # Храмы
    'tanah lot': ['танах лот', 'tanah lot'],
    'uluwatu temple': ['улувату храм', 'uluwatu temple', 'пура улувату'],
    'tirta empul': ['тирта эмпул', 'tirta empul'],
    'besakih': ['бесаких', 'besakih'],
    'lempuyang': ['лемпуянг', 'lempuyang', 'врата небес'],
    'ulun danu': ['улун дану', 'ulun danu'],
    'goa gajah': ['гоа гаджа', 'goa gajah', 'слоновья пещера'],
    'gunung kawi': ['гунунг кави', 'gunung kawi'],
    
    # Рестораны/кафе
    'milk madu': ['милк маду', 'milk madu', 'milk & madu'],
    'crate cafe': ['крейт', 'crate cafe', 'крэйт'],
    'sisterfields': ['систерфилдс', 'sisterfields'],
    'revolver': ['револьвер', 'revolver'],
    'shelter': ['шелтер', 'shelter'],
    'finns': ['финнс', 'finns'],
    'potato head': ['потейто хед', 'потато хед', 'potato head'],
    'la brisa': ['ла бриса', 'la brisa'],
    'motel mexicola': ['мотель мексикола', 'motel mexicola'],
    'la lucciola': ['ла лучиола', 'la lucciola'],
    'ku de ta': ['куде та', 'ku de ta', 'kudeta'],
    'locavore': ['локавор', 'locavore'],
    'mozaic': ['мозаик', 'mozaic'],
    'nook': ['нук', 'nook'],
    'watercress': ['вотеркресс', 'watercress'],
    'kynd': ['кайнд', 'kynd'],
    'zest': ['зест', 'zest'],
    'clear cafe': ['клир кафе', 'clear cafe'],
    'alchemy': ['алхимия', 'alchemy'],
    'kopi luwak': ['копи лювак', 'kopi luwak'],
    
    # Коворкинги
    'dojo': ['доджо', 'dojo'],
    'outpost': ['аутпост', 'outpost'],
    'tropical nomad': ['тропикал номад', 'tropical nomad'],
    'hubud': ['хабуд', 'hubud'],
    'tribal': ['трайбал', 'tribal'],
    
    # Йога/спа
    'yoga barn': ['йога барн', 'yoga barn'],
    'pyramids chi': ['пирамиды чи', 'pyramids of chi', 'пирамиды'],
    'intuitive flow': ['интуитив флоу', 'intuitive flow'],
    'samadi': ['самади', 'samadi'],
    'practice': ['практис', 'the practice'],
    
    # Локации
    'tegallalang': ['тегаллаланг', 'тегалаланг', 'tegallalang', 'рисовые террасы'],
    'campuhan': ['кампуан', 'campuhan ridge'],
    'ubud palace': ['убуд палас', 'ubud palace', 'дворец убуда'],
    'monkey forest': ['манки форест', 'monkey forest', 'лес обезьян'],
    'mount batur': ['батур', 'mount batur', 'гора батур'],
    'mount agung': ['агунг', 'mount agung', 'гора агунг'],
    'nusa penida': ['нуса пенида', 'nusa penida', 'пениде'],
    'nusa lembongan': ['нуса лембонган', 'lembongan'],
    'gili': ['гили', 'gili'],
}

AI_FILTER_PROMPT = """Определи, является ли это сообщение ОБСУЖДЕНИЕМ/ОТЗЫВОМ о месте "{place}" на Бали.

ОБСУЖДЕНИЕ — это:
- Вопрос о месте (как там? стоит ли ехать? как добраться?)
- Отзыв/впечатление (понравилось, не понравилось, рекомендую)
- Совет/рекомендация
- Обсуждение состояния (чисто, грязно, много людей)

НЕ обсуждение:
- Объявление об аренде жилья рядом с местом
- Реклама услуг
- Продажа чего-либо

Сообщение:
{text}

Ответь только: YES или NO"""


async def check_with_ai(place: str, text: str) -> bool:
    """Проверяет через AI — это обсуждение или нет"""
    try:
        response = await client.chat.completions.create(
            model=config.deepseek_model,
            messages=[{"role": "user", "content": AI_FILTER_PROMPT.format(place=place, text=text[:500])}],
            temperature=0,
            max_tokens=10
        )
        answer = response.choices[0].message.content.strip().upper()
        return "YES" in answer
    except Exception as e:
        logging.error(f"AI error: {e}")
        return False


async def find_all_discussions():
    """Ищет все обсуждения мест"""
    await init_db()
    
    all_discussions = {}  # place_key -> [discussions]
    
    async with AsyncSessionMaker() as session:
        # Загружаем ВСЕ сообщения
        result = await session.execute(
            select(ScrapedEvent)
            .where(ScrapedEvent.chat_title != "user_suggest")
            .where(ScrapedEvent.chat_title != "baliforum.ru")
            .where(ScrapedEvent.raw_text.isnot(None))
            .order_by(ScrapedEvent.created_at.desc())
        )
        events = result.scalars().all()
        logging.info(f"📚 Загружено {len(events)} сообщений")
    
    # Ищем упоминания
    for place_key, variants in PLACE_VARIANTS.items():
        discussions = []
        
        for event in events:
            text_lower = event.raw_text.lower()
            
            # Проверяем все варианты названия
            found = False
            for variant in variants:
                if variant.lower() in text_lower:
                    found = True
                    break
            
            if not found:
                continue
            
            # Быстрый фильтр — пропускаем явные объявления
            skip_words = ['сдается', 'сдаётся', 'аренда', 'продается', 'млн в месяц', 'спальни', 'апартаменты', '#реклама']
            if any(sw in text_lower for sw in skip_words):
                continue
            
            discussions.append({
                'text': event.raw_text[:300],
                'link': event.link,
                'chat': event.chat_title,
            })
        
        if discussions:
            all_discussions[place_key] = discussions[:20]  # Макс 20 на место
            logging.info(f"  {place_key}: {len(discussions)} найдено")
    
    logging.info(f"\n📊 Найдено {sum(len(v) for v in all_discussions.values())} упоминаний для {len(all_discussions)} мест")
    
    # Фильтруем через AI
    logging.info("\n🤖 Фильтрация через AI...")
    
    filtered = {}
    for place_key, discussions in all_discussions.items():
        good = []
        for d in discussions[:10]:  # Проверяем первые 10
            is_good = await check_with_ai(place_key, d['text'])
            if is_good:
                good.append({'link': d['link'], 'chat': d['chat'][:25]})
                logging.info(f"  ✅ {place_key}: {d['text'][:50]}...")
            else:
                logging.info(f"  ❌ {place_key}: {d['text'][:50]}...")
            
            if len(good) >= 3:
                break
            
            await asyncio.sleep(0.3)  # Пауза между запросами
        
        if good:
            filtered[place_key] = good
    
    logging.info(f"\n✅ После фильтрации: {sum(len(v) for v in filtered.values())} обсуждений")
    
    # Сохраняем
    with open('discussions_filtered.json', 'w') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    
    return filtered


async def apply_discussions_to_knowledge():
    """Применяет найденные обсуждения к базе знаний"""
    
    with open('discussions_filtered.json') as f:
        discussions = json.load(f)
    
    for json_file in KNOWLEDGE_DIR.glob("*.json"):
        with open(json_file) as f:
            places = json.load(f)
        
        updated = False
        for place in places:
            name = place.get("name", "").lower()
            
            # Ищем совпадение
            for place_key, links in discussions.items():
                variants = PLACE_VARIANTS.get(place_key, [place_key])
                if any(v.lower() in name or name in v.lower() for v in variants):
                    place["mentions"] = links[:3]
                    updated = True
                    break
        
        if updated:
            with open(json_file, 'w') as f:
                json.dump(places, f, ensure_ascii=False, indent=2)
    
    logging.info("✅ Обсуждения добавлены в базу знаний")


if __name__ == "__main__":
    async def main():
        await find_all_discussions()
        await apply_discussions_to_knowledge()
    
    asyncio.run(main())
