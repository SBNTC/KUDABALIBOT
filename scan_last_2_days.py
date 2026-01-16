import sqlite3
import datetime
import time
import random
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError

API_ID = 34319203
API_HASH = 'cc70b0e3398f4284cb134631ab9c4890'
SESSION_NAME = 'server_listener'

# Полный список чатов (93 шт)
CHATS_TO_LISTEN = [
    '@balichatmarket', '@balichat', '@balichatsurfing', '@balichatexchange', '@jobsbali',
    '@balichatservices', '@balichatkid', '@blizkie_bali', '@balichatnash', '@balichat_woman',
    '@balichatarenda', '@baliEast', '@balibeauty', '@voprosBali', '@balisale',
    '@networking_bali', '@balibike', '@balidating', '@balidances', '@balichatdating',
    '@bali_baraholka', '@bali_woman', '@balisurfer', '@balihealth', '@balichatpets',
    '@tantra_blizkie_bali', '@bali_afishaa', '@balichatnews', '@eventsbali', '@balibc',
    '@balichatfit', '@baliktoletit', '@balipackage', '@balifm_afisha', '@baliwomens',
    '@balichatflood', '@networkingbali', '@balifm_media', '@bali_party', '@balichat_photovideo',
    '@pvbali', '@baliyoga', '@bali_visa', '@balida21', '@Bali_buy_sale',
    '@baliexchanges', '@buildbali', '@balirental', '@networkers_bali', '@bali_sharing',
    '@businessmenBali', '@balimassag', '@balichildren', '@blizkie_eventss', '@baliontheway',
    '@redkinvilla', '@designclothing', '@investbali', '@baligames', '@balisp',
    '@balifruits', '@toursbali', '@seobali', '@balimoney', '@baliauto',
    '@baliservice', '@balifood', '@balimc', '@balistop', '@Balibizness',
    '@AI_baliafisha', '@bali_apteka', '@otdam_bali', '@kundalini_bali', '@balibasket',
    '@Bali_House', '@peoplebali', '@honey_villas_indonesia', '@amanitaBali', '@yoganabali',
    '@moneyclubbali', '@baliru', '@bali_znakomstva', '@weetsu_group_bali', '@Quest_Bali',
    '@balirussia', '@BaliManClub', '@baliwomans', '@tranformationgames', '@Balidance',
    '@baliUKR', '@eventmaker_bali', '@balisoul',
]

KEYWORDS = [
    'бесплатн', 'free', 'свободн', 'донейшн', 'donation', 'донат', 
    'оплата по сердцу', 'без оплаты', '0 руб', '0$', 'в подарок', 'gift',
    'пробное', 'пробн', 'первая консультация', 'первая тренировка', 'бесплатная консультация',
    'мастер-класс', 'лекция', 'семинар', 'воркшоп', 'workshop', 'практика', 
    'медитация', 'йога', 'yoga', 'ecstatic', 'dance', 'танц', 'тренер', 'тренировка',
    'консультация', 'диетолог', 'нутрициолог', 'коуч', 'психолог',
    'балерина', 'ballet', 'stretch', 'фитнес', 'спорт',
    'встреча', 'нетворк', 'network', 'завтрак', 'breakfast',
    'вечеринка', 'party', 'концерт', 'dj', 'live', 'выступление', 'клуб', 'bar',
    'stol', 'стол', 'девушки', 'ladies night', 'free drinks', 'алкогол',
    'ретрит', 'retreat', 'тур', 'tour', 'экскурсия',
    'тренинг', 'курс', 'course', 'обучение',
    'приглашаем', 'ждем', 'анонс', 'состоится', 'приходите', 'регистрация'
]

STOP_WORDS = [
    'ищу комнату', 'сниму', 'сдам виллу', 'аренда квартиры',
    'куплю iphone', 'продам macbook'
]

DB_PATH = 'events.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_title TEXT,
            link TEXT UNIQUE,
            raw_text TEXT,
            status TEXT DEFAULT 'pending',
            category TEXT,
            summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Сканируем за 48 часов, чтобы наверняка забрать пропущенное
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    print(f"⏳ Безопасное сканирование (48ч) с {cutoff.strftime('%Y-%m-%d %H:%M')} (UTC)")
    print(f"🐌 Режим: Медленный и аккуратный (паузы 5-10 сек)")

    with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        total_added = 0
        total_chats = len(CHATS_TO_LISTEN)
        
        for idx, chat_link in enumerate(CHATS_TO_LISTEN, 1):
            try:
                # === БЕЗОПАСНАЯ ЗАДЕРЖКА ===
                sleep_time = random.randint(5, 10)
                print(f"💤 [{idx}/{total_chats}] Жду {sleep_time} сек перед {chat_link}...")
                time.sleep(sleep_time)
                # ===========================

                chat_input = chat_link.replace('@', '')
                
                messages = []
                try:
                    limit_check = 0
                    for m in client.iter_messages(chat_input, offset_date=cutoff, reverse=True):
                        messages.append(m)
                        limit_check += 1
                        if limit_check > 50: break 
                except FloodWaitError as e:
                    print(f"⏳ {chat_link}: Флуд-контроль {e.seconds} сек. ПРОПУСКАЮ.")
                    continue
                except Exception as e:
                    print(f"⚠️ {chat_link}: Недоступен ({e})")
                    continue

                count = 0
                for msg in messages:
                    full_text = msg.text if msg.text else ""
                    if not full_text or len(full_text) < 15: 
                        continue
                    
                    text_lower = full_text.lower()
                    
                    if any(s in text_lower for s in STOP_WORDS): continue
                    if not any(k in text_lower for k in KEYWORDS): continue
                    
                    try:
                        chat_title = msg.chat.title if hasattr(msg.chat, 'title') else chat_link
                        username = getattr(msg.chat, 'username', None)
                        link = f"https://t.me/{username}/{msg.id}" if username else f"{chat_link}/{msg.id}"
                    except:
                        chat_title = chat_link
                        link = f"{chat_link}/{msg.id}"

                    cursor.execute("SELECT id FROM scraped_events WHERE link = ?", (link,))
                    if cursor.fetchone(): continue 

                    cursor.execute(
                        "INSERT INTO scraped_events (chat_title, link, raw_text, status) VALUES (?, ?, ?, ?)",
                        (chat_title, link, full_text, 'pending')
                    )
                    count += 1
                    total_added += 1

                if count > 0:
                    conn.commit()
                    print(f"   ✅ Найдено: {count}")
                else:
                    print(f"   ⚪️ Пусто")

            except Exception as e:
                print(f"❌ Ошибка на {chat_link}: {e}")

    conn.close()
    print(f"\n🏁 Сканирование завершено. Добавлено: {total_added}")

if __name__ == "__main__":
    main()
