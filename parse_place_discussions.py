import asyncio
import json
import logging
from telethon import TelegramClient
from telethon.tl.types import Message
from config import config
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Чаты для парсинга обсуждений
CHATS_TO_PARSE = [
    "balichat",
    "bali_chatik", 
    "balichatsurfing",
    "balidating",
    "balichatdating",
    "balisurfer",
    "balibeauty",
]

# Места и их варианты написания
PLACES = {
    "dreamland": ["дримленд", "дримлэнд", "dreamland"],
    "balangan": ["баланган", "балангане", "balangan"],
    "bingin": ["бингин", "bingin"],
    "padang_padang": ["паданг", "padang"],
    "melasti": ["меласти", "melasti"],
    "nyang_nyang": ["ньянг", "нянг", "nyang"],
    "uluwatu": ["улувату", "uluwatu"],
    "jimbaran": ["джимбаран", "jimbaran"],
    "sanur": ["санур", "sanur"],
    "nusa_dua": ["нуса дуа", "nusa dua"],
    "kuta": ["кута", "куте", "kuta"],
    "seminyak": ["семиньяк", "seminyak"],
    "canggu": ["чангу", "canggu"],
    "ubud": ["убуд", "убуде", "ubud"],
    "echo_beach": ["эхо бич", "echo beach"],
    "berawa": ["берава", "berawa"],
    
    # Водопады
    "sekumpul": ["секумпул", "sekumpul"],
    "tegenungan": ["тегенунган", "tegenungan"],
    "gitgit": ["гитгит", "gitgit"],
    "tibumana": ["тибумана", "tibumana"],
    "leke_leke": ["леке леке", "leke leke"],
    "kanto_lampo": ["канто лампо", "kanto lampo"],
    
    # Храмы
    "tanah_lot": ["танах лот", "tanah lot"],
    "tirta_empul": ["тирта эмпул", "tirta empul"],
    "lempuyang": ["лемпуянг", "lempuyang", "врата небес"],
    "besakih": ["бесаких", "besakih"],
    
    # Рестораны
    "finns": ["финнс", "finns"],
    "potato_head": ["потейто", "potato head"],
    "la_brisa": ["ла бриса", "la brisa"],
    "ku_de_ta": ["куде та", "ku de ta"],
    "milk_madu": ["милк маду", "milk madu"],
    "crate_cafe": ["крейт", "crate"],
    "revolver": ["револьвер", "revolver"],
    "shelter": ["шелтер", "shelter"],
    
    # Террасы
    "tegallalang": ["тегаллаланг", "тегалаланг", "tegallalang"],
    
    # Острова
    "nusa_penida": ["нуса пенида", "пениде", "penida"],
    "gili": ["гили", "gili"],
}

# Фильтр — пропускаем объявления
SKIP_WORDS = [
    "сдается", "сдаётся", "аренда", "продается", "продаётся",
    "млн в месяц", "в месяц", "спальни", "апартаменты", "вилла сдам",
    "#реклама", "#аренда", "пишите в лс",
]


async def parse_discussions():
    client = TelegramClient('anon_session', int(config.telegram_api_id), config.telegram_api_hash)
    await client.start()
    
    all_discussions = {place: [] for place in PLACES}
    since = datetime.now() - timedelta(days=90)  # Последние 3 месяца
    
    for chat_name in CHATS_TO_PARSE:
        try:
            logging.info(f"📥 Парсинг {chat_name}...")
            
            count = 0
            async for message in client.iter_messages(chat_name, limit=5000):
                if not message.text or len(message.text) < 20:
                    continue
                
                if message.date.replace(tzinfo=None) < since:
                    break
                
                text_lower = message.text.lower()
                
                # Пропускаем объявления
                if any(sw in text_lower for sw in SKIP_WORDS):
                    continue
                
                # Ищем упоминания мест
                for place_key, variants in PLACES.items():
                    if any(v in text_lower for v in variants):
                        # Формируем ссылку
                        if hasattr(message.chat, 'username') and message.chat.username:
                            link = f"https://t.me/{message.chat.username}/{message.id}"
                        else:
                            link = f"https://t.me/c/{message.chat.id}/{message.id}"
                        
                        # Проверяем дубли
                        if not any(d['link'] == link for d in all_discussions[place_key]):
                            all_discussions[place_key].append({
                                'link': link,
                                'chat': chat_name,
                                'text': message.text[:200],
                                'date': message.date.isoformat(),
                            })
                            count += 1
            
            logging.info(f"  → найдено {count} упоминаний")
            await asyncio.sleep(2)
            
        except Exception as e:
            logging.error(f"❌ {chat_name}: {e}")
    
    await client.disconnect()
    
    # Статистика
    total = sum(len(v) for v in all_discussions.values())
    logging.info(f"\n📊 Всего найдено: {total} обсуждений")
    
    # Сохраняем
    with open('raw_discussions.json', 'w') as f:
        json.dump(all_discussions, f, ensure_ascii=False, indent=2)
    
    # Выбираем лучшие (первые 5 для каждого места)
    filtered = {}
    for place, discussions in all_discussions.items():
        if discussions:
            filtered[place] = [{'link': d['link'], 'chat': d['chat']} for d in discussions[:5]]
    
    with open('discussions_filtered.json', 'w') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    
    logging.info(f"✅ Сохранено: {sum(len(v) for v in filtered.values())} для {len(filtered)} мест")
    
    return filtered


if __name__ == "__main__":
    asyncio.run(parse_discussions())
