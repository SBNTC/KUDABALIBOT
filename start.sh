#!/bin/bash
source venv/bin/activate
pkill -f "python bot.py"
pkill -f "python services/collector.py"

echo "🚀 Запуск коллектора..."
python -c "import asyncio; from services.collector import start_collector; asyncio.run(start_collector())" > collector.log 2>&1 &

echo "🤖 Запуск бота..."
python bot.py
