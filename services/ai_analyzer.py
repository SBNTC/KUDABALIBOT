import google.generativeai as genai
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

async def analyze_event(text: str) -> dict:
    """
    Анализирует текст объявления через Gemini.
    Возвращает dict: {'category': str, 'summary': str}
    """
    # Попробуем использовать стабильную версию flash или pro
    # Если flash не работает, можно попробовать 'gemini-pro'
    model_name = 'gemini-1.5-flash' 
    
    try:
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        Проанализируй текст афиши/объявления.
        
        Задача:
        1. Определи категорию (поле "category"):
           - "free": если бесплатно, донейшн (donation), оплата по сердцу, вход свободный, даром.
           - "paid": если указана цена, стоимость билета, платный вход.
           - "unknown": если неясно.
        2. Напиши краткий заголовок (поле "summary"):
           - До 60 символов.
           - Суть мероприятия (например: "Йога в Убуде", "Бизнес-завтрак").
           - Без эмодзи в начале.

        Текст объявления:
        {text[:2000]}
        
        Ответ верни СТРОГО в формате JSON без markdown-оберток.
        Пример: {{"category": "free", "summary": "Открытый микрофон"}}
        """
        
        response = await model.generate_content_async(prompt)
        
        # Очистка от возможных ```json ... ```
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_text)
        
    except Exception as e:
        logger.error(f"AI Analysis Error with {model_name}: {e}")
        
        # Fallback: Если AI не сработал, пробуем простую эвристику
        text_lower = text.lower()
        category = "unknown"
        if any(w in text_lower for w in ['бесплатно', 'free', 'донейшн', 'donation', 'вход свободный', '0 руб']):
            category = "free"
        elif any(w in text_lower for w in ['цена', 'price', 'idr', 'rub', 'руб', 'стоимость', 'билет']):
            category = "paid"
            
        # Генерируем простое саммари из первой строки
        summary = text.split('\n')[0][:50]
        if len(summary) < 5: # Если первая строка слишком короткая, берем начало текста
             summary = text[:50]
             
        return {"category": category, "summary": summary}
