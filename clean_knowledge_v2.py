import json
from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge_base")

# Мусорные заголовки
SKIP_NAMES = [
    "skip", "editor", "table of", "contents", "links", "sidebar", "picks", 
    "menu", "our best", "our favourite", "ranking", "keep reading", "faq",
    "final thoughts", "conclusion", "related", "subscribe", "newsletter",
    "the best", "honorable", "honourable"
]

def clean_text(text: str) -> str:
    """Убираем мусор из описания"""
    if not text:
        return ""
    # Убираем Skip links и подобное
    for skip in ["Skip to", "Skip links", "EDITOR'S", "Editor's"]:
        if skip in text:
            text = text.split(skip)[0]
    return text.strip()

def is_valid_item(item: dict) -> bool:
    name = item.get("name", "").lower().strip()
    if len(name) < 3 or len(name) > 100:
        return False
    for skip in SKIP_NAMES:
        if skip in name:
            return False
    return True

def process_file(filepath: Path):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cleaned = []
    seen = set()
    
    for item in data:
        if not is_valid_item(item):
            continue
        
        name = item.get("name", "").strip()
        name_key = name.lower()
        
        if name_key in seen:
            continue
        seen.add(name_key)
        
        # Чистим описание
        desc = clean_text(item.get("description", ""))
        
        cleaned.append({
            "name": name,
            "description": desc,
            "address": item.get("address", "").strip(),
            "price": item.get("price", "").strip(),
            "category": item.get("category", "")
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    return len(data), len(cleaned)

def main():
    print("🧹 Очистка базы знаний v2...\n")
    
    for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
        before, after = process_file(json_file)
        print(f"  {json_file.stem}: {before} → {after}")
    
    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
