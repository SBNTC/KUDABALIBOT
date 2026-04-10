# КудаБали — инструкция по запуску

Telegram-бот: афиша событий и гид по местам Бали.

---

## Требования

- Python 3.11+
- Аккаунт Telegram (для Telethon-сканера)
- Бот от [@BotFather](https://t.me/BotFather)
- API-ключ [DeepSeek](https://platform.deepseek.com)
- Telegram API ID/Hash с [my.telegram.org](https://my.telegram.org)

---

## 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

Для парсинга сайтов дополнительно установить браузер Playwright:

```bash
playwright install chromium
```

---

## 2. Настройка .env

Скопировать шаблон и заполнить:

```bash
cp .env.example .env
```

Открыть `.env` и заполнить все поля:

```env
# Токен бота (от @BotFather)
BOT_TOKEN=12345:YOUR_BOT_TOKEN

# Telegram API (my.telegram.org → API development tools)
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=your_api_hash_here

# DeepSeek API (platform.deepseek.com)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Ваш Telegram ID (узнать у @userinfobot)
ADMIN_ID=123456789

# База данных (SQLite по умолчанию, можно заменить на PostgreSQL)
DATABASE_URL=sqlite+aiosqlite:///events.db

# Сколько дней истории сканировать при первом запуске
HISTORY_DAYS=2
```

---

## 3. Инициализация базы данных

```bash
alembic upgrade head
```

Если нужно создать БД с нуля без миграций (для разработки):

```bash
python -c "import asyncio; from database.session import init_db; asyncio.run(init_db())"
```

---

## 4. Первый запуск Telethon (авторизация аккаунта)

При первом запуске Telethon запросит номер телефона и код подтверждения.
Сессия сохраняется в файл `anon_session.session` и больше не запрашивается.

```bash
python -c "
import asyncio
from services.telethon_client import get_client, close_client

async def auth():
    client = await get_client()
    print('Авторизован:', await client.get_me())
    await close_client()

asyncio.run(auth())
"
```

---

## 5. Запуск бота

```bash
python bot.py
```

На Linux/Mac используется `uvloop` автоматически (быстрее стандартного event loop).
На Windows — стандартный asyncio.

---

## 6. Расписание автозадач

Задачи запускаются автоматически через APScheduler:

| Время (Бали, UTC+8) | Задача |
|---|---|
| 06:00 | Парсинг baliforum.ru (Playwright) |
| 08:00 | Сканирование Telegram-чатов (Telethon) |
| 20:00 | Сканирование Telegram-чатов (Telethon) |

После каждого сканирования автоматически: дедупликация → AI-классификация.

---

## 7. Команды администратора

Доступны только пользователю с `ADMIN_ID` из `.env`.

| Команда | Описание |
|---|---|
| `/admin` | Панель управления афишей |
| `/review` | Модерация новых событий |
| `/add` | Создать событие вручную |
| `/clean` | Удалить устаревшие события из review |
| `/dedup` | Удалить точные дубликаты |
| `/dedup_fuzzy` | Удалить похожие события (≥80%) |
| `/stats` | Статистика базы данных |
| `/reload_kb` | Перезагрузить базу знаний мест |
| `/help` | Список всех команд |

---

## 8. Запуск тестов

```bash
pytest tests/
```

Тесты не требуют `.env` и не обращаются к внешним сервисам.

---

## 9. Структура проекта

```
├── bot.py                  # Точка входа
├── config/                 # Настройки (pydantic-settings)
├── database/
│   ├── models.py           # ORM-модели SQLAlchemy
│   ├── session.py          # Engine + AsyncSessionMaker
│   └── requests.py         # Запросы к БД
├── dialogs/
│   ├── feed/               # Диалог ленты событий (aiogram-dialog)
│   ├── admin.py            # Диалог управления афишей
│   └── admin_review.py     # Диалог модерации
├── handlers/
│   ├── admin_panel.py      # Команды администратора
│   └── user/               # Команды пользователя
├── services/
│   ├── analyzer.py         # AI-классификация (DeepSeek)
│   ├── ai_assistant.py     # AI-ассистент по местам
│   ├── collector.py        # Сканирование Telegram-чатов
│   ├── site_parser.py      # Парсинг baliforum.ru (Playwright)
│   ├── dedup.py            # Дедупликация событий
│   ├── reviews_analyzer.py # Анализ отзывов о местах
│   ├── scheduler.py        # Планировщик задач
│   └── telethon_client.py  # Telethon-клиент (singleton)
├── middlewares/
│   ├── throttling.py       # Rate limiting (10 req/min на пользователя)
│   └── db.py               # Сессия БД в контексте хэндлера
├── knowledge_base/         # JSON-файлы с данными о местах Бали
├── alembic/                # Миграции базы данных
└── tests/                  # Unit и интеграционные тесты (101 тест)
```

---

## 10. Переход на PostgreSQL

Заменить строку в `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kudabali
```

Установить драйвер:

```bash
pip install asyncpg
```

Запустить миграции:

```bash
alembic upgrade head
```
