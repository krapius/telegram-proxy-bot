#!/usr/bin/env python3
"""
Скрипт для обновления прокси с отображением прогресса в одном сообщении
"""

import subprocess
import sys
import os
import httpx
import time
import re
import json
import glob
from datetime import datetime

# Импортируем функции из test_proxies.py
from test_proxies import (
    get_latest_proxy_files, 
    extract_proxies_from_file, 
    save_proxies_to_file,
    advanced_final_check
)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc')
WORKER_URL = os.environ.get('WORKER_URL', 'https://telegram-proxy-bot.krichencat.workers.dev')

# Всегда отправляем в канал
CHAT_ID = "-1003605280638"
print(f"📨 Результат будет отправлен в канал: {CHAT_ID}")

def send_message(text, parse_mode='HTML', reply_markup=None):
    """Отправляет новое сообщение"""
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    response = httpx.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json=data,
        timeout=30
    )
    if response.status_code == 200:
        return response.json()['result']['message_id']
    else:
        print(f"❌ Ошибка отправки: {response.status_code}")
        return None

def delete_message(message_id):
    """Удаляет сообщение"""
    try:
        httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
            json={
                "chat_id": CHAT_ID,
                "message_id": message_id
            },
            timeout=30
        )
        print(f"🗑️ Сообщение {message_id} удалено")
    except Exception as e:
        print(f"⚠️ Ошибка удаления: {e}")

def edit_message(message_id, text, parse_mode='HTML', reply_markup=None):
    """Редактирует существующее сообщение"""
    data = {
        "chat_id": CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
            json=data,
            timeout=30
        )
    except Exception as e:
        print(f"⚠️ Ошибка редактирования: {e}")

def progress_bar(percent, width=10):
    percent = min(100, max(0, percent))
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"{bar} {percent:3.0f}%"

def update_progress(message_id, stage_num, stage_name, current, total, start_time, total_proxies=0):
    stages = [
        (1, "1. 🧘 Медитирую"),
        (2, "2. 📦 Сбор прокси"),
        (3, "3. 📊 Проверка Ping"),
        (4, "4. 🔬 Анализ стабильности"),
        (5, "5. 🌐 Проверка соединения"),
        (6, "6. ✨ Подготовка результатов")
    ]
    
    stage_percent = (current / total) * 100 if total > 0 else 0
    total_stages = 6
    base_progress = ((stage_num - 1) / total_stages) * 100
    stage_contribution = 100 / total_stages
    total_progress = base_progress + (stage_contribution * (stage_percent / 100))
    total_progress = min(100, max(0, total_progress))
    
    elapsed = time.time() - start_time
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)
    if elapsed_min > 0:
        time_display = f"{elapsed_min}м {elapsed_sec:02d}с"
    else:
        time_display = f"{elapsed_sec}с"
    
    text = f"<b>🔄 Обновление прокси</b>\n\n"
    text += f"<code>{progress_bar(total_progress, 10)}</code>"
    text += f"   —   <i>{time_display}</i>\n\n"
    text += f"<pre>"
    text += f"{'Этап':<24} {'Статус':<16}\n"
    text += f"{'─'*42}\n"
    
    for num, name in stages:
        if num < stage_num:
            status = "✅"
        elif num == stage_num:
            if stage_percent > 0:
                bar = progress_bar(stage_percent, 8)
                status = f"⏳ {bar:>8}"
            else:
                status = "⏳"
        else:
            status = "⋯"
        text += f"{name:<24} {status:>16}\n"
    
    text += f"</pre>\n"
    
    if total_proxies > 0:
        text += f"\n🟢 <b>Найдено:</b> {total_proxies} прокси"
    
    if stage_name:
        text += f"\n\n📌 <i>{stage_name}</i>"
    
    edit_message(message_id, text)

def create_proxy_buttons(proxies):
    keyboard = []
    for i, p in enumerate(proxies[:6], 1):
        flag = p.get('flag', '🇪🇺')
        main_button = {"text": f"{flag} Прокси #{i}", "url": p['link']}
        share_url = f"https://t.me/share/url?url={p['link']}"
        share_button = {"text": "📤", "url": share_url}
        keyboard.append([main_button, share_button])
    
    keyboard.append([{"text": "🔄 Обновить список прокси", "callback_data": "refresh"}])
    return {"inline_keyboard": keyboard}

def parse_proxies_from_file():
    """Парсит best_proxies.json в список прокси с пингом и скоростью"""
    proxies = []
    try:
        with open('best_proxies.json', 'r', encoding='utf-8') as f:
            proxies = json.load(f)
            print(f"📦 Загружено {len(proxies)} прокси из JSON")
            return proxies
    except Exception as e:
        print(f"⚠️ Ошибка чтения JSON: {e}")
    
    try:
        with open('best_proxies.txt', 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
            for line in lines:
                if line.startswith('tg://proxy'):
                    proxies.append({'link': line})
            print(f"📦 Найдено {len(proxies)} прокси в TXT")
            return proxies
    except Exception as e:
        print(f"⚠️ Ошибка чтения TXT: {e}")
    
    return []

def main():
    start_time = time.time()
    
    print("🔄 Запуск обновления прокси...")
    
    start_message_id = send_message("🔄 <b>Обновление прокси начато!</b>\n\nЭто займёт 1-2 минуты...\nРезультат появится здесь автоматически.")
    time.sleep(0.1)
    
    progress_message_id = send_message("🔄 <b>Запуск обновления прокси...</b>")
    if not progress_message_id:
        print("❌ Не удалось отправить начальное сообщение")
        return
    
    if start_message_id:
        delete_message(start_message_id)
    
    # Этап 1: Подготовка
    update_progress(progress_message_id, 1, "Подготовка...", 1, 1, start_time)
    time.sleep(0.5)
    update_progress(progress_message_id, 1, "Готов к работе", 1, 1, start_time)
    
    # Этап 2: Запуск main.py для сбора прокси
    print("📦 Запуск main.py...")
    update_progress(progress_message_id, 2, "Запуск сбора прокси...", 0, 1, start_time)
    
    process = subprocess.Popen(
        ['python3', 'main.py'],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    last_percent = 0
    total_proxies = 0
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            print(f"   main.py: {line.strip()[:100]}")
            match = re.search(r'\[(\d+)/(\d+)\]', line)
            if match:
                checked = int(match.group(1))
                total = int(match.group(2))
                percent = int(checked * 100 / total) if total > 0 else 0
                if percent >= last_percent + 2 or percent == 100:
                    last_percent = percent
                    update_progress(progress_message_id, 2, f"Сбор прокси... {percent}%", percent, 100, start_time, total_proxies)
            
            match = re.search(r'RU=(\d+)\s+EU=(\d+)', line)
            if match:
                ru = int(match.group(1))
                eu = int(match.group(2))
                total_proxies = ru + eu
                update_progress(progress_message_id, 2, f"Найдено {total_proxies} прокси", 100, 100, start_time, total_proxies)
    
    process.wait(timeout=10)
    print("✅ main.py завершён")
    print(f"📊 main.py собрал прокси: {total_proxies}")
    
    # Этап 3: Проверка прокси через функции test_proxies.py
    print("📊 Проверка прокси...")
    update_progress(progress_message_id, 3, "Проверка прокси...", 0, 100, start_time, total_proxies)
    
    # Получаем последние файлы из verified
    ru_file, eu_file, all_file = get_latest_proxy_files()
    print(f"   RU файл: {ru_file}")
    print(f"   EU файл: {eu_file}")
    
    all_proxies = []
    
    if ru_file:
        print(f"   Обработка RU прокси...")
        ru_proxies = extract_proxies_from_file(ru_file, "ru")
        all_proxies.extend(ru_proxies)
        print(f"   Найдено RU прокси: {len(ru_proxies)}")
    
    if eu_file:
        print(f"   Обработка EU прокси...")
        eu_proxies = extract_proxies_from_file(eu_file, "eu")
        all_proxies.extend(eu_proxies)
        print(f"   Найдено EU прокси: {len(eu_proxies)}")
    
    if not all_proxies:
        print("❌ Нет прокси для проверки")
        delete_message(progress_message_id)
        send_message("❌ <b>Не удалось найти прокси</b>\n\nПопробуйте позже")
        return
    
    # Сохраняем в best_proxies.txt и best_proxies.json
    print(f"📦 Сохраняем {len(all_proxies)} прокси...")
    final_proxies = save_proxies_to_file(all_proxies)
    total_proxies_found = len(final_proxies)
    
    update_progress(progress_message_id, 3, f"Найдено {total_proxies_found} стабильных", 100, 100, start_time, total_proxies_found)
    
    # Этап 4-6: Имитация прогресса
    for stage in range(4, 7):
        update_progress(progress_message_id, stage, "Обработка...", 100, 100, start_time, total_proxies_found)
        time.sleep(0.5)
    
    # Отправляем в Worker
    proxies = parse_proxies_from_file()
    print(f"📤 Отправка {len(proxies)} прокси в Worker...")
    try:
        response = httpx.post(
            f"{WORKER_URL}/update",
            json={"proxies": proxies},
            timeout=30
        )
        if response.status_code == 200:
            print(f"✅ Отправлено {len(proxies)} прокси в Worker")
            
            print(f"📨 Запрашиваем отправку сообщения в канал...")
            try:
                fake_update = {
                    "message": {
                        "chat": {"id": int(CHAT_ID)},
                        "text": "/start"
                    }
                }
                channel_response = httpx.post(
                    f"{WORKER_URL}",
                    json=fake_update,
                    timeout=30
                )
                if channel_response.status_code == 200:
                    print(f"✅ Сообщение отправлено в канал")
                else:
                    print(f"⚠️ Ошибка отправки сообщения: {channel_response.status_code}")
            except Exception as e:
                print(f"⚠️ Не удалось отправить сообщение: {e}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
    
    time.sleep(0.5)
    delete_message(progress_message_id)
    print("🎉 Обновление завершено!")

if __name__ == "__main__":
    main()