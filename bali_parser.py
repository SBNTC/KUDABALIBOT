import asyncio
import aiohttp
import json
import re
from bs4 import BeautifulSoup
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

OUTPUT_DIR = Path("knowledge_base")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SOURCES = {
    "beaches": [
        "https://thehoneycombers.com/bali/bali-beaches-guide/",
        "https://finnsbeachclub.com/guides/best-beaches-bali/",
    ],
    "coworkings": [
        "https://thehoneycombers.com/bali/coworking-spaces-bali/",
        "https://finnsbeachclub.com/guides/best-cafes-digital-nomads-work-bali/",
        "https://finnsbeachclub.com/guides/best-coworking-spaces-bali/",
    ],
    "temples": [
        "https://thehoneycombers.com/bali/bali-temples-guide/",
        "https://finnsbeachclub.com/guides/best-temples-bali/",
    ],
    "waterfalls": [
        "https://thehoneycombers.com/bali/bali-waterfalls/",
        "https://finnsbeachclub.com/guides/best-waterfalls-bali/",
    ],
    "surf_spots": [
        "https://thehoneycombers.com/bali/surfing-in-bali-guide/",
        "https://finnsbeachclub.com/guides/bali-surf-guide/",
    ],
    "clinics": [
        "https://thehoneycombers.com/bali/hospitals-and-clinics-in-bali/",
        "https://finnsbeachclub.com/guides/hospitals-clinics-bali/",
    ],
    "restaurants_canggu": [
        "https://thehoneycombers.com/bali/best-restaurants-in-canggu/",
        "https://finnsbeachclub.com/guides/best-restaurants-canggu-bali/",
    ],
    "restaurants_seminyak": [
        "https://thehoneycombers.com/bali/where-to-eat-seminyak-best-restaurants/",
        "https://finnsbeachclub.com/guides/best-restaurants-seminyak/",
    ],
    "restaurants_ubud": [
        "https://thehoneycombers.com/bali/where-to-eat-ubud-best-restaurants/",
        "https://finnsbeachclub.com/guides/best-ubud-restaurants-dining-bali/",
    ],
    "restaurants_uluwatu": [
        "https://thehoneycombers.com/bali/where-to-eat-uluwatu-best-restaurants/",
        "https://finnsbeachclub.com/guides/best-restaurants-uluwatu/",
    ],
    "cafes": [
        "https://thehoneycombers.com/bali/best-cafes-in-bali/",
        "https://finnsbeachclub.com/guides/best-cafes-bali/",
    ],
    "yoga": [
        "https://thehoneycombers.com/bali/best-yoga-studios-bali/",
        "https://finnsbeachclub.com/guides/best-yoga-studios-bali/",
    ],
    "activities": [
        "https://thehoneycombers.com/bali/things-to-do-in-bali/",
        "https://finnsbeachclub.com/guides/things-to-do-bali/",
    ],
}


async def fetch_page(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url, headers=HEADERS, timeout=30) as resp:
            if resp.status == 200:
                return await resp.text()
            logging.warning(f"❌ {resp.status}: {url}")
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
    return None


def extract_items(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        name = heading.get_text(strip=True)
        
        # Чистим номера типа "1.", "2." в начале
        name = re.sub(r'^\d+\.\s*', '', name)
        
        if not name or len(name) < 3 or len(name) > 150:
            continue
        
        skip_words = ['more', 'related', 'also read', 'share', 'comment', 'guide to', 'our pick', 'honourable', 'map of', 'faq', 'frequently']
        if any(w in name.lower() for w in skip_words):
            continue
        
        description = ""
        address = ""
        price = ""
        
        for sibling in heading.find_next_siblings(['p', 'ul', 'div'])[:5]:
            text = sibling.get_text(strip=True)
            if text and len(text) > 30 and not description:
                description = text[:600]
            
            # Ищем адрес
            addr_match = re.search(r'(Jl\.?|Jalan)\s*[A-Za-z\s\d\.\-,]+', text)
            if addr_match and not address:
                address = addr_match.group(0)[:100]
            
            # Ищем цену
            price_match = re.search(r'(IDR|Rp\.?)\s*[\d\.,]+k?', text, re.IGNORECASE)
            if price_match and not price:
                price = price_match.group(0)
        
        items.append({
            "name": name,
            "description": description,
            "address": address,
            "price": price,
            "category": category,
        })
    
    return items


async def parse_category(session: aiohttp.ClientSession, category: str, urls: list[str]) -> list[dict]:
    all_items = []
    seen = set()
    
    for url in urls:
        logging.info(f"📥 {category}: {url}")
        html = await fetch_page(session, url)
        if not html:
            continue
        
        items = extract_items(html, category)
        
        for item in items:
            key = item['name'].lower()[:50]
            if key not in seen:
                seen.add(key)
                all_items.append(item)
        
        logging.info(f"  → {len(items)} элементов")
        await asyncio.sleep(1)
    
    return all_items


async def main():
    logging.info("🚀 Парсер базы знаний Бали v2")
    
    async with aiohttp.ClientSession() as session:
        for category, urls in SOURCES.items():
            items = await parse_category(session, category, urls)
            
            if items:
                output_file = OUTPUT_DIR / f"{category}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                logging.info(f"✅ {category}: {len(items)} → {output_file}")
            else:
                logging.warning(f"⚠️ {category}: пусто")
    
    logging.info("🏁 Готово!")
    
    print("\n📊 ИТОГО:")
    total = 0
    for json_file in sorted(OUTPUT_DIR.glob("*.json")):
        with open(json_file) as f:
            count = len(json.load(f))
            total += count
            print(f"  {json_file.stem}: {count}")
    print(f"\n  ВСЕГО: {total} элементов")


if __name__ == "__main__":
    asyncio.run(main())

# Дополнительный парсинг
SOURCES_V2 = {
    "temples": [
        "https://finnsbeachclub.com/guides/temples-in-bali/",
        "https://thehoneycombers.com/bali/temples-in-bali/",
    ],
    "clinics": [
        "https://finnsbeachclub.com/guides/best-hospitals-bali/",
        "https://thehoneycombers.com/bali/bali-hospitals-clinics/",
    ],
    "surf_spots": [
        "https://finnsbeachclub.com/guides/surfing-bali/",
        "https://thehoneycombers.com/bali/bali-surf-spots/",
    ],
    "yoga": [
        "https://finnsbeachclub.com/guides/yoga-in-bali/",
        "https://thehoneycombers.com/bali/yoga-in-bali/",
    ],
    "spas": [
        "https://finnsbeachclub.com/guides/best-spas-bali/",
        "https://thehoneycombers.com/bali/best-spas-in-bali/",
    ],
    "clubs": [
        "https://finnsbeachclub.com/guides/best-clubs-bali/",
        "https://thehoneycombers.com/bali/best-nightclubs-bali/",
    ],
    "hotels": [
        "https://finnsbeachclub.com/guides/best-hotels-bali/",
        "https://thehoneycombers.com/bali/best-hotels-in-bali/",
    ],
}
