#!/usr/bin/env python3
import httpx
import os
import sys

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc')
CHAT_ID = "305673438"

def send_message(text):
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=30
        )
        return response.status_code == 200
    except:
        return False

def progress_bar(percent, width=10):
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"{bar} {percent:3.0f}%"

# Отправляем начальное сообщение
send_message("🔄 <b>Обновление прокси начато!</b>\n\nЭто займёт 1-2 минуты...")

# Здесь будет логика обновления с отправкой прогресса
# Шаг 1: сбор прокси
send_message("📦 <b>Этап 1/3: Сбор сырых прокси...</b>\n\n" + progress_bar(0))

# ... после выполнения main.py
send_message("📦 <b>Этап 1/3: Сбор сырых прокси...</b>\n\n" + progress_bar(100))

# Шаг 2: проверка
send_message("📊 <b>Этап 2/3: Проверка и фильтрация...</b>\n\n" + progress_bar(0))

# ... после выполнения test_proxies.py
send_message("📊 <b>Этап 2/3: Проверка и фильтрация...</b>\n\n" + progress_bar(100))

# Шаг 3: отправка
send_message("📤 <b>Этап 3/3: Отправка в Cloudflare...</b>\n\n" + progress_bar(0))

# ... после отправки
send_message("📤 <b>Этап 3/3: Отправка в Cloudflare...</b>\n\n" + progress_bar(100))

# Финальное сообщение
send_message("✅ <b>Обновление завершено!</b>\n\nПрокси обновлены. Отправьте /start для просмотра.")