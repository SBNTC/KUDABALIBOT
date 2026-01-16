import json
import asyncio
import logging
from pathlib import Path
from openai import AsyncOpenAI
from config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

client = AsyncOpenAI(
    api_key=config.deepseek_api_key.get_secret_value(),
    base_url=config.deepseek_base_url
)

KNOWLEDGE_DIR = Path("knowledge_base")

TRANSLATE_PROMPT = """Ты переводчик. Переведи данные о местах на Бали на русский язык.

ПРАВИЛА:
1. Названия мест НЕ переводи (оставь на английском)
2. Описания переведи на русский, кратко (1-2 предложения)
3. Удали мусорные записи (FAQ, вопросы типа "How much", "Why is", статьи не о конкретных местах)
4. Оставь только реальные места (рестораны, пляжи, студии и т.д.)

Входные данные (JSON):
{data}

Верни JSON массив в формате:
[{{"name": "Original Name", "description": "Описание на русском", "address": "адрес", "price": "цена"}}]

Только JSON, без markdown!
"""

async def translate_batch(items: list) -> list:
    """Переводит пачку записей"""
    if not items:
        return []
    
    try:
        prompt = TRANSLATE_PROMPT.format(data=json.dumps(items[:15], ensure_ascii=False))
        
        response = await client.chat.completions.create(
            model=config.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        
        raw = response.choices[0].message.content or "[]"
        
        # Чистим от markdown
        raw = raw.replace("```json", "").replace("```", "").strip()
        
        # Ищем JSON массив
        import re
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        return []
    except Exception as e:
        logging.error(f"Translate error: {e}")
        return []


async def process_file(filepath: Path):
    """Обрабатывает один файл"""
    logging.info(f"📄 {filepath.stem}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        return
    
    # Фильтруем очевидный мусор перед отправкой
    skip_patterns = ["how much", "why is", "what is", "do bali", "night surfing", "halal food", "skip to", "editor"]
    filtered = []
    for item in data:
        name = item.get("name", "").lower()
        if any(p in name for p in skip_patterns):
            continue
        if len(name) < 3 or len(name) > 80:
            continue
        filtered.append(item)
    
    # Переводим пачками по 15
    translated = []
    for i in range(0, len(filtered), 15):
        batch = filtered[i:i+15]
        result = await translate_batch(batch)
        translated.extend(result)
        logging.info(f"  Переведено: {len(translated)}/{len(filtered)}")
        await asyncio.sleep(1)  # Пауза между запросами
    
    # Сохраняем
    if translated:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ {filepath.stem}: {len(data)} → {len(translated)}")
    else:
        logging.warning(f"⚠️ {filepath.stem}: пусто после перевода")


async def main():
    logging.info("🌐 Перевод базы знаний на русский...\n")
    
    files = sorted(KNOWLEDGE_DIR.glob("*.json"))
    for f in files:
        await process_file(f)
        await asyncio.sleep(2)
    
    logging.info("\n🏁 Готово!")


if __name__ == "__main__":
    asyncio.run(main())
