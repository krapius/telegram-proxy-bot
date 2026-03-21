#!/usr/bin/env python3
import httpx
import re
import os

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc')
WORKER_URL = os.environ.get('WORKER_URL', 'https://telegram-proxy-bot.krichencat.workers.dev')
CHAT_ID = "305673438"

STATUS = os.environ.get('STATUS', 'unknown')
STATUS_TEXT = "✅ Успешно" if STATUS == "success" else "❌ Ошибка"
EMOJI = "🎉" if STATUS == "success" else "⚠️"

try:
    response = httpx.get(WORKER_URL, timeout=10)
    match = re.search(r'Прокси в кэше: (\d+)', response.text)
    proxies_count = match.group(1) if match else "неизвестно"
except:
    proxies_count = "неизвестно"

message = f"""{EMOJI} <b>Обновление прокси</b>

<b>Статус:</b> {STATUS_TEXT}
<b>Прокси в кэше:</b> {proxies_count}
<b>Время:</b> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

/start - показать список
/refresh - обновить вручную
"""

try:
    response = httpx.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
        timeout=30
    )
    print(f"📢 Уведомление отправлено: {response.status_code}")
except Exception as e:
    print(f"⚠️ Не удалось отправить уведомление: {e}")
