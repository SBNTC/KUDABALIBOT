import os
from dotenv import load_dotenv, find_dotenv
import google.generativeai as genai

def main():
    # 1. Явный поиск и загрузка .env
    env_path = find_dotenv()
    print(f"📂 Путь к файлу .env: {env_path if env_path else 'НЕ НАЙДЕН'}")

    if not env_path:
        print("❌ Ошибка: Файл .env не найден в текущей директории.")
        return

    # override=True заставит перезаписать переменные
    loaded = load_dotenv(env_path, override=True)
    print(f"🔄 Результат загрузки переменных: {loaded}")

    # 2. Проверка ключа
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ Ошибка: Переменная GOOGLE_API_KEY пустая или отсутствует.")
        return

    print(f"✅ Ключ найден: {api_key[:6]}...******")

    # 3. Запрос к API
    genai.configure(api_key=api_key)
    
    print("\n📡 Запрашиваю список доступных моделей...")
    try:
        found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"🔹 Модель доступна: {m.name}")
                found = True
        
        if not found:
            print("⚠️ Модели не найдены. Проверьте права ключа.")
            
    except Exception as e:
        print(f"\n❌ Ошибка API запроса: {e}")

if __name__ == "__main__":
    main()
