import json
from pathlib import Path

OUTPUT_DIR = Path("knowledge_base")

# Данные из твоего docx (основные рестораны по районам)
RESTAURANTS_DATA = {
    "restaurants_canggu": [
        {"name": "FINNS Beach Club", "description": "Beach club с интернациональной кухней, обеды/ужины, тусовка", "address": "Jl. Pantai Berawa No.99, Canggu", "price": "300k-700k"},
        {"name": "Uma Garden", "description": "Grill / современная кухня, ужин, свидание", "address": "Jl. Umalas 1 No.8, Kerobokan", "price": "350k-800k"},
        {"name": "Shun Omakase", "description": "Японская omakase, особый ужин, свидание", "address": "Jl. Pantai Berawa No.99, Tibubeneng", "price": "800k-2000k"},
        {"name": "Hippie Fish", "description": "Seafood с видом на пляж, ужин, свидание", "address": "Jl. Pantai Pererenan No.171", "price": "400k-1000k"},
        {"name": "Te Amo Gastro Bistro", "description": "Европейская bistro, паста/пицца", "address": "Jl. Munduk Catu, Canggu", "price": "250k-600k"},
        {"name": "Kong", "description": "Bistro с коктейлями, ужин, свидание", "address": "Jl. Pantai Berawa No.14b", "price": "300k-800k"},
        {"name": "Shelter", "description": "Mediterranean + Middle Eastern fusion", "address": "Jl. Pantai Pererenan No.133", "price": "350k-900k"},
        {"name": "BAKED", "description": "Bakery + brunch, завтраки, можно с ноутбуком", "address": "Jl. Pantai Pererenan No.118", "price": "150k-350k"},
        {"name": "Milk & Madu", "description": "Brunch / pizza, завтраки, семья/дети, работа днём", "address": "Jl Pantai Berawa No.52", "price": "120k-300k"},
        {"name": "Crate Cafe", "description": "Breakfast/brunch cafe, завтраки, быстрый кофе", "address": "Jl Canggu Padang Linjong No.49", "price": "120k-250k"},
        {"name": "Skool Kitchen", "description": "Dinner 'kissed by fire', ужин, свидание, впечатления", "address": "Jl. Pura Dalem, Canggu", "price": "500k-1500k"},
        {"name": "Luma", "description": "Mediterranean, ужин, свидание", "address": "Jl. Pantai Batu Bolong No.91", "price": "400k-1000k"},
        {"name": "Lacalita Bar Y Cocina", "description": "Mexican, ужин, компания, коктейли", "address": "Jl. Pantai Batu Bolong No.68", "price": "250k-700k"},
        {"name": "Mason", "description": "Fine dining / grill, ужин, свидание/бизнес-ужин", "address": "Jl. Pantai Batu Bolong No.39a", "price": "400k-1200k"},
        {"name": "One Eyed Jack", "description": "Japanese izakaya, ужин, свидание", "address": "Jl. Pantai Berawa No.c89", "price": "400k-1200k"},
    ],
    "restaurants_pererenan": [
        {"name": "Bar Vera", "description": "Bistro / Wine Bar, вино, ужин, стиль", "address": "Jl. Pantai Pererenan", "price": "350k-700k"},
        {"name": "WOODS", "description": "Jazz / Global, джаз, спокойный ужин", "address": "Jl. Dalem Lingsir", "price": "250k-500k"},
        {"name": "Tribal", "description": "Coworking / Cafe, работа, нетворкинг", "address": "Gg. Tribal", "price": "150k-250k"},
        {"name": "Honey Kitchen", "description": "Brunch / Cafe, завтрак, бранч", "address": "Jl. Pantai Pererenan", "price": "150k-250k"},
        {"name": "RiZE", "description": "Indian / Brunch, доса, индийский завтрак", "address": "Jl. Pantai Pererenan", "price": "120k-200k"},
        {"name": "Fuego", "description": "Argentine Grill, стейки, мясо", "address": "Jl. Dalem Lingsir", "price": "300k-600k"},
        {"name": "Pescado", "description": "Spanish / Paella, паэлья, морепродукты", "address": "Jl. Pantai Pererenan", "price": "200k-400k"},
        {"name": "Touché", "description": "All-day dining, завтрак, модный ланч", "address": "Jl. Pantai Pererenan", "price": "150k-300k"},
        {"name": "Roots", "description": "Healthy / Salad Bar, ЗОЖ, веган, обед", "address": "Jl. Pantai Pererenan", "price": "120k-200k"},
        {"name": "Boheme", "description": "Restaurant / Pool, чилл у бассейна", "address": "Jl. Pantai Pererenan", "price": "200k-400k"},
        {"name": "Warung Yess", "description": "Local / Indonesian, дешево, локал фуд", "address": "Jl. Pantai Pererenan", "price": "30k-80k"},
    ],
    "restaurants_seminyak": [
        {"name": "Merah Putih", "description": "Indonesian fine dining, ужин, особый повод", "address": "Jl Petitenget No.100x", "price": "180k++"},
        {"name": "Mama San", "description": "Pan-Asian, ужин, коктейли", "address": "Jl Raya Kerobokan No.135", "price": "160k++"},
        {"name": "La Lucciola", "description": "Italian / beachfront, закат, свидание", "address": "Jl Kayu Aya, Petitenget Temple", "price": "160k++"},
        {"name": "Saltlick", "description": "Steakhouse, свидание, стейки", "address": "Jl Kayu Aya No.9", "price": "230k++"},
        {"name": "Barbacoa", "description": "Latin American grill, ужин, мясо/гриль", "address": "Jl Petitenget No.14", "price": "180k++"},
        {"name": "Motel Mexicola", "description": "Mexican, ужин + тусовка", "address": "Jl Kayu Jati No.9x, Petitenget", "price": "160k++"},
        {"name": "Mauri", "description": "Italian fine dining, fine dining, свидание", "address": "Jl Petitenget No.100", "price": "290k++"},
        {"name": "Sisterfields", "description": "All-day brunch, завтрак/ланч, популярное место", "address": "Jl Kayu Cendana No.7", "price": "95k++"},
        {"name": "KYND", "description": "Vegan cafe, веган, инстаграм", "address": "Jl Raya Petitenget No.12x", "price": "100k-200k"},
        {"name": "Cafe Organic", "description": "Vegetarian/healthy, ЗОЖ-завтрак", "address": "Jl Petitenget No.99x", "price": "100k-200k"},
        {"name": "Revolver Espresso", "description": "Specialty coffee, кофе, бранч", "address": "Jl Kayu Aya Gang 51", "price": "50k-150k"},
        {"name": "Da Maria", "description": "Italian / party vibe, ужин, шумно/весело", "address": "Jl. Petitenget No.170", "price": "200k-500k"},
        {"name": "Sardine", "description": "Seafood + rice paddies, ужин, вид на поля", "address": "Jl. Petitenget No.21", "price": "250k-600k"},
    ],
    "restaurants_kuta": [
        {"name": "Kuta Social Club", "description": "Rooftop / Seafood / Grill, закаты, коктейли, свидание", "address": "Mamaka by Ovolo, Jl. Pantai Kuta", "price": "150k++"},
        {"name": "Poppies Restaurant", "description": "International / Indonesian, романтика, ужин в саду", "address": "Poppies Lane I, Kuta", "price": "95k++"},
        {"name": "Made's Warung", "description": "Indonesian classic, локальная еда, история, семья", "address": "Jl. Pantai Kuta, Banjar Pande Mas", "price": "60k++"},
        {"name": "Fat Chow", "description": "Pan-Asian fusion, ужин, вкусно и недорого", "address": "Poppies Lane II No.7C", "price": "85k++"},
        {"name": "Hard Rock Cafe", "description": "American / Burgers, музыка, бургеры, семья", "address": "Jl. Pantai Kuta", "price": "180k++"},
        {"name": "Warung Laota", "description": "Chinese Hong Kong porridge, похмельный суп, ужин компанией", "address": "Jl. Raya Kuta No.530, Tuban", "price": "60k++"},
    ],
    "restaurants_ubud": [
        {"name": "Locavore NXT", "description": "Modern Local / Degustation, гастро-трип, must visit", "address": "Jl. A.A. Gede Rai (Mas)", "price": "1950k++"},
        {"name": "Mozaic", "description": "French-Indonesian Fine Dining, романтика, легенда Убуда", "address": "Jl. Raya Sanggingan", "price": "1100k++"},
        {"name": "Room4Dessert", "description": "Dessert Degustation, десертный сет (Netflix Chef's Table)", "address": "Jl. Sanggingan", "price": "1090k++"},
        {"name": "Hujan Locale", "description": "Modern Indonesian / Asian, ужин, вкусно и красиво", "address": "Jl. Sri Wedari No.5", "price": "125k++"},
        {"name": "Copper Kitchen & Bar", "description": "Rooftop / Earth-to-table, руфтоп, закат, романтика", "address": "Bisma Eight Hotel, Jl. Bisma", "price": "95k++"},
        {"name": "Sayan House", "description": "Japanese-Latin Fusion, вид на джунгли, закат, коктейли", "address": "Jl. Raya Sayan No.70", "price": "130k++"},
        {"name": "Zest", "description": "Vegan / Creative, ЗОЖ-тусовка, вид, ноутбук", "address": "Jl. Penestanan Kelod No.8", "price": "78k++"},
        {"name": "Clear Cafe", "description": "Healthy / Vegetarian, красивый интерьер, без обуви, релакс", "address": "Jl. Hanoman No.8", "price": "40k++"},
        {"name": "Seniman Coffee", "description": "Specialty Coffee, кофе-гики, работа", "address": "Jl. Sri Wedari No.5", "price": "35k++"},
        {"name": "Warung Biah Biah", "description": "Balinese Tapas, попробовать всё по чуть-чуть, дешево", "address": "Jl. Pengosekan", "price": "25k++"},
        {"name": "Alchemy", "description": "Raw Vegan, ЗОЖ легенда, салат-бар, десерты", "address": "Jl. Penestanan Kelod", "price": "75k++"},
    ],
    "restaurants_bukit": [
        {"name": "Masonry", "description": "Wood-fired Mediterranean, ужин, стильно, друзья", "address": "Uluwatu", "price": "120k++"},
        {"name": "Bartolo", "description": "European Bistro / Cocktails, свидание, коктейли, must visit", "address": "Uluwatu", "price": "110k++"},
        {"name": "Suka Espresso Uluwatu", "description": "Australian Cafe, завтрак после серфа, ноутбук", "address": "Uluwatu", "price": "65k++"},
        {"name": "El Kabron", "description": "Spanish / Seafood, закат, паэлья, праздник", "address": "Pecatu", "price": "200k++"},
        {"name": "Menega Cafe", "description": "Seafood BBQ, классика, ужин на песке, закат", "address": "Jimbaran Bay", "price": "150k++"},
        {"name": "Sundara", "description": "Fine Dining / Grill, роскошный закат, 5* сервис", "address": "Jimbaran Bay", "price": "250k++"},
        {"name": "Cuca Flavor", "description": "Tapas / Molecular, гастрономия, свидание (топ!)", "address": "Jimbaran", "price": "680k++"},
        {"name": "Koral Restaurant", "description": "Fine Dining (Aquarium), ужин в аквариуме, вау-эффект", "address": "Nusa Dua, Kempinski", "price": "1500k++"},
        {"name": "Sundays Beach Club", "description": "International, день на пляже, костер вечером", "address": "Ungasan", "price": "300k++"},
    ],
}

def main():
    print("📥 Импорт ресторанов из docx...\n")
    
    for category, restaurants in RESTAURANTS_DATA.items():
        output_file = OUTPUT_DIR / f"{category}.json"
        
        # Загружаем существующие
        existing = []
        if output_file.exists():
            with open(output_file) as f:
                existing = json.load(f)
        
        seen = {r['name'].lower() for r in existing}
        added = 0
        
        for r in restaurants:
            if r['name'].lower() not in seen:
                existing.append({
                    "name": r['name'],
                    "description": r['description'],
                    "address": r.get('address', ''),
                    "price": r.get('price', ''),
                    "category": category,
                })
                added += 1
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        
        print(f"  {category}: +{added} новых, итого {len(existing)}")
    
    print("\n✅ Импорт завершён!")
    
    # Статистика
    print("\n📊 ОБЩАЯ СТАТИСТИКА:")
    total = 0
    for json_file in sorted(OUTPUT_DIR.glob("*.json")):
        with open(json_file) as f:
            count = len(json.load(f))
            total += count
            print(f"  {json_file.stem}: {count}")
    print(f"\n  ВСЕГО: {total} элементов")

if __name__ == "__main__":
    main()
