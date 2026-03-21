#!/bin/bash
# Скрипт для обновления прокси

cd /Users/artem/projects/telegram-proxy-collector/proxy
source ../venv/bin/activate

echo "🔄 Начинаю обновление прокси..."
python send_proxies_to_worker.py

echo ""
echo "✅ Готово!"