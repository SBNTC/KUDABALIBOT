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

# Новые категории
SOURCES = {
    "temples": [
        "https://finnsbeachclub.com/guides/temples-in-bali/",
        "https://finnsbeachclub.com/guides/bali-temples/",
        "https://thehoneycombers.com/bali/temples-in-bali/",
        "https://thehoneycombers.com/bali/bali-temple-guide/",
    ],
    "clinics": [
        "https://finnsbeachclub.com/guides/best-hospitals-bali/",
        "https://finnsbeachclub.com/guides/hospitals-bali/",
        "https://thehoneycombers.com/bali/bali-hospitals-clinics/",
        "https://thehoneycombers.com/bali/hospitals-clinics-bali/",
    ],
    "surf_spots": [
        "https://finnsbeachclub.com/guides/surfing-bali/",
        "https://finnsbeachclub.com/guides/bali-surfing/",
        "https://finnsbeachclub.com/guides/surf-spots-bali/",
        "https://thehoneycombers.com/bali/bali-surf-spots/",
        "https://thehoneycombers.com/bali/surfing-bali/",
    ],
    "yoga": [
        "https://finnsbeachclub.com/guides/yoga-in-bali/",
        "https://finnsbeachclub.com/guides/yoga-bali/",
        "https://finnsbeachclub.com/guides/best-yoga-bali/",
        "https://thehoneycombers.com/bali/yoga-in-bali/",
        "https://thehoneycombers.com/bali/yoga-studios-bali/",
    ],
    "spas": [
        "https://finnsbeachclub.com/guides/best-spas-bali/",
        "https://finnsbeachclub.com/guides/spas-bali/",
        "https://thehoneycombers.com/bali/best-spas-in-bali/",
        "https://thehoneycombers.com/bali/spas-bali/",
    ],
    "clubs": [
        "https://finnsbeachclub.com/guides/best-clubs-bali/",
        "https://finnsbeachclub.com/guides/nightlife-bali/",
        "https://finnsbeachclub.com/guides/beach-clubs-bali/",
        "https://thehoneycombers.com/bali/best-nightclubs-bali/",
        "https://thehoneycombers.com/bali/beach-clubs-bali/",
    ],
    "markets": [
        "https://finnsbeachclub.com/guides/markets-bali/",
        "https://thehoneycombers.com/bali/markets-in-bali/",
        "https://thehoneycombers.com/bali/bali-markets/",
    ],
    "diving": [
        "https://finnsbeachclub.com/guides/diving-bali/",
        "https://finnsbeachclub.com/guides/snorkeling-bali/",
        "https://thehoneycombers.com/bali/diving-bali/",
    ],
}

SKIP_NAMES = [
    "table of contents", "our best", "our favourite", "our favorite",
    "ranking upfront", "keep reading", "quick guide", "map of", "faq",
    "frequently asked", "final thoughts", "in conclusion", "wrapping up",
    "bottom line", "related posts", "you may also", "share this",
]

async def fetch_page(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url, headers=HEADERS, timeout=30) as resp:
            if resp.status == 200:
                return await resp.text()
            logging.warning(f"❌ {resp.status}: {url}")
    except Exception as e:
        logging.error(f"Error: {url} - {e}")
    return None


def extract_items(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        name = heading.get_text(strip=True)
        name = re.sub(r'^\d+\.\s*', '', name)
        
        if not name or len(name) < 4 or len(name) > 150:
            continue
        
        if any(skip in name.lower() for skip in SKIP_NAMES):
            continue
        
        description = ""
        address = ""
        price = ""
        
        for sibling in heading.find_next_siblings(['p', 'ul', 'div'])[:5]:
            text = sibling.get_text(strip=True)
            if text and len(text) > 30 and not description:
                description = text[:600]
            
            addr_match = re.search(r'(Jl\.?|Jalan)\s*[A-Za-z\s\d\.\-,]+', text)
            if addr_match and not address:
                address = addr_match.group(0)[:100]
            
            price_match = re.search(r'(IDR|Rp\.?)\s*[\d\.,]+k?', text, re.IGNORECASE)
            if price_match and not price:
                price = price_match.group(0)
        
        if description:  # Только с описанием
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
    logging.info("🚀 Парсер v2 - дополнительные категории")
    
    async with aiohttp.ClientSession() as session:
        for category, urls in SOURCES.items():
            # Проверяем существует ли уже файл
            output_file = OUTPUT_DIR / f"{category}.json"
            existing = []
            if output_file.exists():
                with open(output_file) as f:
                    existing = json.load(f)
                logging.info(f"📂 {category}: уже есть {len(existing)} элементов")
            
            items = await parse_category(session, category, urls)
            
            if items:
                # Объединяем с существующими
                seen = {i['name'].lower()[:50] for i in existing}
                for item in items:
                    if item['name'].lower()[:50] not in seen:
                        existing.append(item)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
                logging.info(f"✅ {category}: итого {len(existing)}")
            else:
                logging.warning(f"⚠️ {category}: ничего нового")
    
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
