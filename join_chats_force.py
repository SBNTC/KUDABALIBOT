from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import FloodWaitError
import time
import random
import os

API_ID = 34319203
API_HASH = 'cc70b0e3398f4284cb134631ab9c4890'
SESSION_NAME = 'server_listener'
PROGRESS_FILE = 'joined_list.txt'

CHATS = [
    '@balichatnews', '@businessmenBali', '@Balibizness', 
    '@networkers_bali', '@bali_party', '@balifm_afisha', 
    '@blizkie_eventss',
    '@balichat', '@balichatdating', '@balichatik', '@balichatnash', 
    '@networkingbali', '@voprosBali', '@baliRU', '@Peoplebali', 
    '@bali_360', '@balichatflood', '@balistop', '@baliEast', 
    '@baliUKR', '@bali_laika', '@balidating', '@plus49',
    '@artbali', '@bali_tusa', '@eventsbali', '@balievents', 
    '@baligames', '@truth_in_cinema', '@pvbali',
    '@balisp', '@balipractice', '@Balidance', '@balisoul', 
    '@baliyoga', 'https://t.me/joinchat/DFnrTxWkiKiqLqUPi0Wd4g',
    '@redkinvilla', '@balimassag', '@ArtTherapyBali', 
    '@tranformationgames', 'https://t.me/joinchat/ACQha0XLsqxUzRBUDw_g0A',
    '@domanabali', '@domanabalichat', '@balichatarenda', 
    '@balirental', '@VillaUbud', '@bali_house', '@allAbout_Bali', 
    '@balibike', '@baliauto', '@rentcarbaliopen',
    '@balifruits', '@balifood', '@balihealth', '@RAWBali',
    '@balibc', 'https://t.me/joinchat/LGbIw1D5VLfx3ixzddlQ5A', 
    '@balida21', '@seobali', '@jobsbali', '@balimc', '@BaliManClub',
    '@indonesia_bali',
    '@balichat_woman', '@bali_woman', '@baliwomans', '@balibeauty',
    '@balirussia', '@balipackage', '@balichatmarket', 
    '@bali_baraholka', '@balisale', '@bali_sharing', 
    '@Bali_buy_sale', '@designclothing', '@balimoney',
    '@balichildren', '@roditelibali', 
    '@balifootball', '@balibasket', '@balisurfer'
]

def load_processed():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_processed(link):
    with open(PROGRESS_FILE, 'a') as f:
        f.write(f"{link}\n")

with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
    processed = load_processed()
    print(f"📂 Загружено {len(processed)} обработанных чатов.")
    
    chats_to_process = [c for c in CHATS if c not in processed]
    print(f"🚀 Осталось обработать: {len(chats_to_process)}")
    
    for link in chats_to_process:
        # По умолчанию большая задержка (если реально вступим)
        current_delay = random.randint(60, 100)
        
        try:
            print(f"➡️ Пробую: {link}")
            if 'joinchat' in link or '+' in link:
                try:
                    hash_arg = link.split('/')[-1].replace('+', '')
                    client(ImportChatInviteRequest(hash_arg))
                    print("   ✅ Успех (Invite)")
                except FloodWaitError as e:
                    print(f"   ⏳ FLOOD WAIT: Жду {e.seconds} секунд...")
                    time.sleep(e.seconds + 5)
                    try:
                        client(ImportChatInviteRequest(hash_arg))
                        print("   ✅ Успех (Invite после паузы)")
                    except: pass
                except Exception as e:
                    if "UserAlreadyParticipant" in str(e):
                        print("   🆗 Уже там (Быстрый скип)")
                        current_delay = 2 # БЫСТРЫЙ ПЕРЕХОД
                    else:
                        print(f"   ❌ Ошибка Invite: {e}")
            else:
                username = link.replace('@', '').replace('https://t.me/', '')
                try:
                    client(JoinChannelRequest(username))
                    print("   ✅ Успех (Join)")
                except FloodWaitError as e:
                    print(f"   ⏳ FLOOD WAIT: Жду {e.seconds} секунд...")
                    time.sleep(e.seconds + 5)
                    try:
                        client(JoinChannelRequest(username))
                        print("   ✅ Успех (Join после паузы)")
                    except: pass
                except Exception as e:
                    if "UserAlreadyParticipant" in str(e):
                        print("   🆗 Уже там (Быстрый скип)")
                        current_delay = 2 # БЫСТРЫЙ ПЕРЕХОД
                    else:
                        print(f"   ❌ Ошибка Join: {e}")

            save_processed(link)
            
            print(f"   💤 Сплю {current_delay} сек...")
            time.sleep(current_delay)

        except Exception as main_e:
            print(f"   ⚠️ Общая ошибка: {main_e}")

    print("\n🏁 Готово!")
