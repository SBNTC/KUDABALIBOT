import json
from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge_base")

# Мусорные заголовки которые нужно удалить
SKIP_NAMES = [
    "table of contents",
    "our best",
    "our favourite", 
    "our favorite",
    "ranking upfront",
    "keep reading",
    "quick guide",
    "map of",
    "faq",
    "frequently asked",
    "final thoughts",
    "in conclusion",
    "wrapping up",
    "bottom line",
    "related posts",
    "you may also",
    "share this",
    "leave a comment",
    "about the author",
    "more from",
    "subscribe",
    "newsletter",
    "join our",
    "follow us",
]

def is_valid_item(item: dict) -> bool:
    name = item.get("name", "").lower()
    
    # Пропускаем короткие имена
    if len(name) < 4:
        return False
    
    # Пропускаем мусорные заголовки
    for skip in SKIP_NAMES:
        if skip in name:
            return False
    
    # Пропускаем если нет описания и имя слишком общее
    if not item.get("description") and len(name) < 15:
        return False
    
    return True

def clean_file(filepath: Path) -> int:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data)
    cleaned = [item for item in data if is_valid_item(item)]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    removed = original_count - len(cleaned)
    return removed, len(cleaned)

def main():
    print("🧹 Очистка базы знаний...\n")
    
    total_removed = 0
    total_remaining = 0
    
    for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
        removed, remaining = clean_file(json_file)
        total_removed += removed
        total_remaining += remaining
        print(f"  {json_file.stem}: удалено {removed}, осталось {remaining}")
    
    print(f"\n✅ Готово! Удалено: {total_removed}, Всего: {total_remaining}")

if __name__ == "__main__":
    main()
