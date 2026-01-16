#!/bin/bash
cd /root/events_bot
source venv/bin/activate

echo "=== $(date) ===" >> /var/log/bali_bot.log

# Скрейпим новые посты
python3 scan_last_2_days.py >> /var/log/bali_bot.log 2>&1

# Запускаем AI анализ через бота
python3 << 'PYEOF'
import asyncio
from services.analyzer import run_batch_analysis

asyncio.run(run_batch_analysis())
PYEOF

echo "✅ Завершено" >> /var/log/bali_bot.log
