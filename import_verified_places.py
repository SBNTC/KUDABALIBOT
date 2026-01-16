import json
from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge_base")

# Места от пользователей, разбитые по категориям
VERIFIED_PLACES = {
    "restaurants_canggu": [
        {"name": "YUKI Canggu", "description": "Японский ресторан высокого уровня"},
        {"name": "Vue Canggu", "description": "Ресторан с видом, современная кухня"},
        {"name": "MILU By Nook", "description": "Стильный ресторан от команды Nook"},
        {"name": "Passo by Nook", "description": "Итальянская кухня, паста"},
        {"name": "ARTE Canggu", "description": "Пиццерия с авторской пиццей"},
        {"name": "Waroeng Sushi Canggu", "description": "Доступные суши, локальный фаворит"},
        {"name": "Ramen Hamatora Canggu", "description": "Аутентичный японский рамен"},
        {"name": "Casa Tua Canggu", "description": "Итальянский ресторан, домашняя атмосфера"},
        {"name": "Warung Local", "description": "Местная индонезийская кухня, недорого"},
        {"name": "L'Osteria Pizza e Cucina Canggu", "description": "Итальянская пицца и паста"},
        {"name": "KONG | Contemporary Bistro Chic", "description": "Современное бистро, коктейли"},
        {"name": "MASONRY. Restaurant Canggu", "description": "Гриль, средиземноморская кухня"},
        {"name": "Pasta Dealer Bali", "description": "Свежая паста, итальянская кухня"},
        {"name": "The Slow Kitchen and Bar", "description": "Атмосферный ресторан, здоровая еда"},
        {"name": "Moana Fish Eatery", "description": "Морепродукты, поке боулы"},
        {"name": "Secret Spot Canggu", "description": "Скрытое место, уютная атмосфера"},
        {"name": "Milk & Madu Berawa", "description": "Завтраки, пицца, семейное место"},
        {"name": "Milk & Madu Beach Road", "description": "Филиал популярного кафе"},
        {"name": "Crate Cafe", "description": "Популярное место для завтраков"},
        {"name": "3MONGKIS ISLAND - Berawa", "description": "Островная атмосфера, коктейли"},
        {"name": "Shofuku Ramen Bar - Berawa", "description": "Японский рамен бар"},
    ],
    "restaurants_seminyak": [
        {"name": "Kilo Kitchen Bali - Seminyak", "description": "Азиатский фьюжн, креативные блюда"},
        {"name": "Kunti 3 Sushi Bar", "description": "Суши бар, японская кухня"},
        {"name": "Revolver Seminyak", "description": "Кофейня в переулке, отличный кофе"},
        {"name": "Watercress Seminyak", "description": "Здоровая еда, салаты, боулы"},
        {"name": "BRAUD Cafe Seminyak", "description": "Скандинавская выпечка, кофе"},
        {"name": "Sisterfields", "description": "Австралийский бранч, популярное место"},
        {"name": "Pison, Petitenget", "description": "Кофейня для работы, хороший wifi"},
        {"name": "Японский ресторан Окамура Бали", "description": "Аутентичная японская кухня"},
        {"name": "Motel Mexicola", "description": "Мексиканская кухня, вечеринки, яркий интерьер"},
        {"name": "KU DE TA", "description": "Легендарный бич-клаб, закаты, fine dining"},
    ],
    "restaurants_ubud": [
        {"name": "Pesona Lounge Ubud", "description": "Лаунж с видом, расслабленная атмосфера"},
        {"name": "L'Osteria Pizza e Cucina Ubud", "description": "Итальянская пицца в Убуде"},
        {"name": "Kebun Bistro", "description": "Бистро в саду, органические продукты"},
        {"name": "Balinese Home Cooking", "description": "Домашняя балийская кухня"},
        {"name": "Montana Del Cafe", "description": "Кафе с видом на рисовые поля"},
        {"name": "The Rice Joglo", "description": "Традиционный дом, индонезийская кухня"},
        {"name": "Livingstone", "description": "Колониальный стиль, международная кухня"},
        {"name": "Warung Goûthé", "description": "Французская выпечка в Убуде"},
    ],
    "restaurants_uluwatu": [
        {"name": "Mana Uluwatu Restaurant & Bar", "description": "Ресторан с видом на океан"},
        {"name": "The CLOUDS Uluwatu", "description": "Ресторан на скалах, закаты"},
        {"name": "Le Cliff Bali", "description": "Fine dining на утёсе"},
        {"name": "Suka Espresso Uluwatu", "description": "Австралийское кафе, завтраки после сёрфа"},
        {"name": "Sundays Beach Club", "description": "Бич-клаб, день у океана"},
    ],
    "restaurants_pererenan": [
        {"name": "The Shady Pig", "description": "Мясной ресторан, стейки, бургеры"},
        {"name": "Kinoa Pererenan", "description": "Здоровая еда, боулы, смузи"},
        {"name": "WOODS PERERENAN", "description": "Джаз, уютная атмосфера, коктейли"},
        {"name": "ACME Pererenan", "description": "Кафе и бар, бранчи"},
        {"name": "Pescado Bali Pererenan", "description": "Испанская кухня, морепродукты, паэлья"},
        {"name": "Touché Cafe & Restaurant", "description": "Модный бранч, завтраки весь день"},
        {"name": "Honey,", "description": "Кафе для бранча, уютное место"},
        {"name": "Shelter Restaurant", "description": "Middle Eastern, гриль, топовое место"},
    ],
    "cafes": [
        {"name": "Blacklist Coffee Roasters", "description": "Спешелти кофе, своя обжарка"},
        {"name": "HUGO ESPRESSO", "description": "Качественный эспрессо"},
        {"name": "Revolver Canggu", "description": "Культовая кофейня, скрытая локация"},
        {"name": "Bread Basket Bakery - Canggu Bali", "description": "Свежая выпечка, хлеб"},
        {"name": "ZIN Cafe", "description": "Кафе при йога-центре"},
        {"name": "Ettore Gelato Berawa", "description": "Итальянское мороженое"},
        {"name": "SATUSATU COFFEE COMPANY", "description": "Локальный спешелти кофе"},
        {"name": "Butterman", "description": "Кафе, выпечка, сэндвичи"},
        {"name": "Usha cafe&bakery Kerobokan", "description": "Пекарня, здоровые завтраки"},
        {"name": "Cafe Coach", "description": "Кофе, работа с ноутбуком"},
        {"name": "Lusa By/Suka", "description": "От команды Suka Espresso"},
        {"name": "BGS Bali Canggu", "description": "Кофе-бар + сёрф-шоп"},
        {"name": "The Common", "description": "Кофейня, коворкинг вайб"},
        {"name": "MIEL SPECIALTY COFFEE CANGGU", "description": "Спешелти кофе, коворкинг"},
        {"name": "BAKED.", "description": "Выпечка, завтраки, кофе"},
        {"name": "BAKED. Berawa", "description": "Филиал популярной пекарни"},
        {"name": "SENSORIUM Bali", "description": "Гастро-кафе, креативные завтраки"},
        {"name": "Hungry Bird Coffee Roaster", "description": "Своя обжарка, отличный кофе"},
        {"name": "Copenhagen", "description": "Скандинавский стиль, выпечка"},
        {"name": "Crate Cafe", "description": "Популярные завтраки, всегда очередь"},
        {"name": "Rise & Shine Cafe Canggu", "description": "Завтраки, здоровая еда"},
        {"name": "Suka Espresso Ubud", "description": "Австралийский кофе в Убуде"},
        {"name": "I Am Vegan Babe", "description": "Веганское кафе, боулы"},
        {"name": "Starbucks Reserve Dewata", "description": "Самый большой Старбакс в мире"},
        {"name": "STARBUCKS CANGGU", "description": "Старбакс с хорошим wifi"},
        {"name": "Guna N Buah", "description": "Фрукты, смузи, здоровая еда"},
    ],
    "coworkings": [
        {"name": "Tribal Bali Coworking Hostel", "description": "Коворкинг + хостел, комьюнити"},
        {"name": "The Flow Bali", "description": "Коворкинг, быстрый интернет"},
        {"name": "Outsite Bali - Pererenan", "description": "Коливинг для номадов"},
        {"name": "Tropical Nomad Coworking Space", "description": "Коворкинг в центре Чангу"},
        {"name": "Genesis Creative Centre", "description": "Креативное пространство"},
        {"name": "Outpost Canggu Coworking", "description": "Популярный коворкинг, бассейн"},
        {"name": "Dojo Bali Coworking", "description": "Легендарный коворкинг (закрыт)"},
    ],
    "beaches": [
        {"name": "Nyang Nyang Beach", "description": "Дикий пляж, мало людей, красивый"},
        {"name": "Padang Padang Beach", "description": "Известный пляж из фильма, сёрфинг"},
        {"name": "Balangan Beach", "description": "Белый песок, сёрф-спот, варунги"},
        {"name": "Dreamland Beach", "description": "Белый песок, волны, красивый вид"},
        {"name": "Bingin Beach", "description": "Сёрф-спот, атмосфера старого Бали"},
        {"name": "Melasti Beach", "description": "Белоснежный песок, фотогеничный"},
        {"name": "Pantai Batu Bolong", "description": "Главный пляж Чангу, закаты"},
        {"name": "Karma Beach", "description": "Приватный пляж, доступ платный"},
        {"name": "Jimbaran Beach", "description": "Морепродукты на закате"},
        {"name": "Sanur Beach", "description": "Спокойный пляж, семьи, снорклинг"},
        {"name": "Nusa Dua Beach", "description": "Чистый пляж, отели, спокойно"},
        {"name": "Amed Beach", "description": "Снорклинг, дайвинг, тихо"},
        {"name": "Pemuteran Beach", "description": "Север Бали, дайвинг, рифы"},
        {"name": "Padang Bai Beach", "description": "Порт на Гили, снорклинг рядом"},
        {"name": "Keramas Beach", "description": "Сёрф-спот, чёрный песок"},
        {"name": "Diamond Beach", "description": "Нуса Пенида, открыточный вид"},
        {"name": "Geger Beach", "description": "Спокойный пляж в Нуса Дуа"},
    ],
    "surf_spots": [
        {"name": "Pantai Batu Bolong", "description": "Главный спот Чангу, для всех уровней"},
        {"name": "Bingin Beach", "description": "Рифовый брейк, средний/продвинутый"},
        {"name": "Padang Padang Beach", "description": "Легендарный спот, трубы"},
        {"name": "Balangan Beach", "description": "Лефт, для среднего уровня"},
        {"name": "Uluwatu Beach", "description": "Мировой спот, только для про"},
        {"name": "Keramas Beach", "description": "Ночной сёрфинг, быстрые волны"},
        {"name": "Big Brother Surf Camp", "description": "Сёрф-кемп, обучение"},
        {"name": "Surf Motel Camp & Surf School", "description": "Школа сёрфинга + проживание"},
    ],
    "yoga": [
        {"name": "Soham Wellness Center", "description": "Йога, веллнес, детокс"},
        {"name": "The Practice", "description": "Топовая йога-студия в Чангу"},
        {"name": "Udara Bali Yoga Detox & Spa", "description": "Йога + детокс программы"},
        {"name": "The Yoga Barn", "description": "Легендарная йога-студия Убуда"},
        {"name": "SAMADI Yoga & Wellness Center", "description": "Йога, эко-кафе"},
        {"name": "POWER + REVIVE STUDIO", "description": "Силовая йога, фитнес"},
        {"name": "Pyramids Of Chi", "description": "Звуковые медитации в пирамидах"},
    ],
    "spas": [
        {"name": "Espace Spa", "description": "Спа высокого уровня"},
        {"name": "Putri Ubud Spa 2", "description": "Традиционный балийский спа"},
        {"name": "Cantika Zest", "description": "Натуральная косметика, спа"},
        {"name": "Karsa Spa", "description": "Спа с видом на рисовые поля"},
        {"name": "Spring Spa Canggu", "description": "Современный спа в Чангу"},
        {"name": "Lotus Massage Therapy Canggu", "description": "Массаж, доступные цены"},
        {"name": "Balinese SPA Club", "description": "Традиционные процедуры"},
        {"name": "SUNDARI Wellness", "description": "Веллнес-центр"},
        {"name": "Bodyworks Spa", "description": "Популярный спа, массаж"},
        {"name": "Estetica Belle", "description": "Косметология, уход"},
    ],
    "clubs": [
        {"name": "Mrs Sippy Bali", "description": "Бич-клаб с бассейном, вечеринки"},
        {"name": "NEON PALMS", "description": "Бар, коктейли, яркий интерьер"},
        {"name": "Motel Mexicola", "description": "Мексиканский бар, тусовки"},
        {"name": "Sama-Sama Reggae Bar", "description": "Регги бар, расслабленная атмосфера"},
        {"name": "La Brisa Bali", "description": "Бич-клаб из переработанных материалов"},
        {"name": "Potato Head Beach Club", "description": "Культовый бич-клаб, закаты"},
        {"name": "Café del Mar Bali", "description": "Известный бренд, электронная музыка"},
        {"name": "Palmilla Bali Beach Club", "description": "Бич-клаб, бассейн"},
        {"name": "Mano Beach House", "description": "Бич-хаус, еда и коктейли"},
        {"name": "The Lawn", "description": "Газон у пляжа, закаты, коктейли"},
        {"name": "KU DE TA", "description": "Легендарный клуб Семиньяка"},
    ],
    "waterfalls": [
        {"name": "Gitgit Waterfall", "description": "Известный водопад на севере"},
        {"name": "Tibumana Waterfall", "description": "Красивый водопад рядом с Убудом"},
        {"name": "Banyumala Waterfall", "description": "Двойной водопад, можно купаться"},
        {"name": "Aling-Aling Waterfall", "description": "Прыжки в воду, несколько уровней"},
        {"name": "Kanto Lampo Waterfall", "description": "Фотогеничный водопад"},
        {"name": "Nungnung Waterfall", "description": "Высокий водопад, много ступеней"},
        {"name": "Tegenungan Waterfall", "description": "Популярный водопад рядом с Убудом"},
        {"name": "Sekumpul Waterfall", "description": "Самый красивый водопад Бали"},
    ],
    "temples": [
        {"name": "Pura Luhur Uluwatu", "description": "Храм на скале, закаты, танец Кечак"},
        {"name": "Pura Tanah Lot", "description": "Храм на воде, культовое место"},
        {"name": "Pura Tirta Empul", "description": "Священный источник, очищение"},
        {"name": "Pura Besakih", "description": "Мать всех храмов, главный храм Бали"},
        {"name": "Pura Taman Ayun", "description": "Красивый королевский храм"},
        {"name": "Pura Gunung Kawi Sebatu", "description": "Храм с источниками, тихо"},
        {"name": "Ulun Danu Beratan Temple", "description": "Храм на озере, открыточный вид"},
        {"name": "Penataran Agung Lempuyang Temple", "description": "Врата в небеса, фото"},
        {"name": "Goa Gajah", "description": "Слоновья пещера, древний храм"},
        {"name": "Pura Taman Kemuda Saraswati", "description": "Храм с лотосами в Убуде"},
    ],
    "activities": [
        {"name": "Campuhan Ridge Walk", "description": "Прогулка по хребту, рассвет"},
        {"name": "Tegalalang Rice Terraces", "description": "Знаменитые рисовые террасы"},
        {"name": "Jatiluwih Rice Terraces", "description": "ЮНЕСКО, масштабные террасы"},
        {"name": "Sidemen Rice Terrace", "description": "Тихая альтернатива Тегалалангу"},
        {"name": "Penglipuran Village", "description": "Традиционная балийская деревня"},
        {"name": "Ubud Palace", "description": "Королевский дворец, танцы вечером"},
        {"name": "Karang Boma Cliff", "description": "Обрыв для фото, вид на океан"},
        {"name": "Lake Tamblingan", "description": "Озеро в горах, каноэ"},
        {"name": "Marigold Fields", "description": "Поля бархатцев, фото"},
        {"name": "Bajra Sandhi Monument", "description": "Монумент в Денпасаре"},
        {"name": "Badung Market", "description": "Традиционный рынок, фрукты"},
        {"name": "Beachwalk Shopping Center", "description": "Торговый центр в Куте"},
        {"name": "Deus Ex Machina", "description": "Мото-культура, кафе, магазин"},
    ],
    "clinics": [
        {"name": "Hydro Medical Clinic Canggu", "description": "Капельницы, вакцины, стоматология"},
    ],
    "hotels": [
        {"name": "Ulaman Eco Luxury Resort", "description": "Эко-резорт, бамбуковые виллы"},
        {"name": "Māua Nusa Penida", "description": "Бутик-отель на Нуса Пенида"},
        {"name": "Villa Palm River", "description": "Вилла у реки"},
        {"name": "The Wave Hotel Pererenan", "description": "Отель для сёрферов"},
        {"name": "Hidden Hills Villas", "description": "Виллы с бассейнами, приватно"},
        {"name": "The Korowai Bali", "description": "Дома на деревьях"},
        {"name": "The Asa Maia", "description": "Бутик-резорт, рисовые поля"},
        {"name": "The Apartments Ubud", "description": "Апартаменты в Убуде"},
        {"name": "Ubud Valley Boutique Resort", "description": "Бутик-резорт в долине"},
        {"name": "Sehuli Retreat", "description": "Ретрит-центр"},
        {"name": "Munduk Cabins", "description": "Домики в горах на севере"},
        {"name": "Sumberkima Hill Retreat", "description": "Ретрит на холме"},
        {"name": "Aria Villas Ubud", "description": "Приватные виллы в Убуде"},
        {"name": "Aksari Resort & Spa Ubud", "description": "Резорт со спа"},
        {"name": "The Laguna Bali", "description": "5-звёздочный резорт в Нуса Дуа"},
        {"name": "Nirjhara", "description": "Эксклюзивный эко-резорт"},
        {"name": "Alila Villas Uluwatu", "description": "Люксовые виллы на скале"},
        {"name": "Adiwana Resort Jembawan", "description": "Резорт в Убуде"},
        {"name": "Wapa di Ume Sidemen", "description": "Резорт в Сидемене, виды"},
        {"name": "Jimbaran Puri, A Belmond Hotel", "description": "Люксовый отель в Джимбаране"},
        {"name": "SIWA Resorts, Lombok", "description": "Резорт на Ломбоке"},
        {"name": "Rimbun Canggu", "description": "Виллы в Чангу"},
        {"name": "The Wina Villa Canggu", "description": "Вилла в Чангу"},
        {"name": "The Kamare", "description": "Бутик-отель"},
        {"name": "Canggu Hype Suites", "description": "Сьюты в Чангу"},
        {"name": "Aeera Villa Canggu", "description": "Вилла в Чангу"},
        {"name": "Manca Villa Canggu", "description": "Вилла в Чангу"},
        {"name": "ZIN Berawa Villas", "description": "Виллы и бунгало"},
        {"name": "Citadines Berawa Beach Bali", "description": "Апарт-отель"},
        {"name": "La Pan Nam Exotic Villas", "description": "Экзотические виллы"},
    ],
    "fitness": [
        {"name": "Avenue Fitness", "description": "Современный фитнес-зал"},
        {"name": "Victory Fitness Club", "description": "Тренажёрный зал"},
        {"name": "Wanderlust Fitness Village", "description": "Фитнес на природе"},
        {"name": "Body Factory Bali", "description": "Кроссфит, функциональный тренинг"},
    ],
    "shops": [
        {"name": "Country Textile Canggu", "description": "Ткани, текстиль"},
        {"name": "Foxy Activewear", "description": "Спортивная одежда"},
        {"name": "Foxy Activewear Ubud", "description": "Филиал в Убуде"},
        {"name": "Periplus Bookshop", "description": "Книжный магазин"},
        {"name": "Hedonist store Bali", "description": "Дизайнерские вещи"},
        {"name": "Bali Hijack Sandals", "description": "Сандалии ручной работы"},
        {"name": "Muka Concepts", "description": "Концепт-стор"},
        {"name": "Indigo", "description": "Магазин одежды"},
        {"name": "Jet Black Ginger", "description": "Интерьер, декор"},
        {"name": "Mimpi Grocery", "description": "Органические продукты"},
        {"name": "Pepito Market Canggu", "description": "Супермаркет, импортные продукты"},
    ],
    "services": [
        {"name": "Quick Laundry", "description": "Прачечная, быстро"},
        {"name": "7 Days Laundry", "description": "Прачечная"},
        {"name": "Central Kuta Money Exchange", "description": "Обмен валют, хороший курс"},
    ],
    "islands": [
        {"name": "Nusa Penida", "description": "Остров с драматичными видами, дикая природа"},
        {"name": "Nusa Ceningan", "description": "Маленький остров, спокойно"},
        {"name": "Nusa Lembongan", "description": "Снорклинг, мангровые леса"},
        {"name": "Pulau Menjangan", "description": "Лучший дайвинг и снорклинг"},
        {"name": "Gili Islands", "description": "Три острова без транспорта"},
        {"name": "Flores", "description": "Остров с драконами Комодо"},
    ],
    "districts": [
        {"name": "Lovina", "description": "Север Бали, дельфины, чёрный песок, тихо"},
        {"name": "Amed", "description": "Восток Бали, дайвинг, снорклинг, спокойно"},
        {"name": "Sidemen", "description": "Рисовые террасы, вулкан Агунг, тихо"},
        {"name": "Munduk", "description": "Горный район, водопады, прохладно"},
        {"name": "Candidasa", "description": "Восток, снорклинг, лагуна"},
        {"name": "Pemuteran", "description": "Север, дайвинг, рифы"},
    ],
}

def main():
    print("📥 Импорт проверенных мест...\n")
    
    for category, places in VERIFIED_PLACES.items():
        output_file = KNOWLEDGE_DIR / f"{category}.json"
        
        # Загружаем существующие
        existing = []
        if output_file.exists():
            with open(output_file, encoding='utf-8') as f:
                existing = json.load(f)
        
        seen = {p.get("name", "").lower() for p in existing}
        added = 0
        
        for place in places:
            if place["name"].lower() not in seen:
                existing.append({
                    "name": place["name"],
                    "description": place["description"],
                    "address": place.get("address", ""),
                    "price": place.get("price", ""),
                    "verified": True,  # Метка проверено
                    "category": category
                })
                added += 1
                seen.add(place["name"].lower())
        
        # Помечаем существующие совпадения как проверенные
        for p in existing:
            for verified in places:
                if p.get("name", "").lower() == verified["name"].lower():
                    p["verified"] = True
                    if not p.get("description") or len(p.get("description", "")) < 10:
                        p["description"] = verified["description"]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        
        verified_count = sum(1 for p in existing if p.get("verified"))
        print(f"  {category}: +{added} новых, {verified_count} проверенных, всего {len(existing)}")
    
    print("\n✅ Импорт завершён!")
    
    # Итого
    total = 0
    verified = 0
    for f in KNOWLEDGE_DIR.glob("*.json"):
        with open(f) as file:
            data = json.load(file)
            total += len(data)
            verified += sum(1 for p in data if p.get("verified"))
    
    print(f"\n📊 Всего: {total} мест, из них {verified} проверенных")

if __name__ == "__main__":
    main()
