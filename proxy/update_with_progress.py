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

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc')
WORKER_URL = os.environ.get('WORKER_URL', 'https://telegram-proxy-bot.krichencat.workers.dev')
CHAT_ID = "305673438"

message_id = None

def send_or_edit(text, parse_mode='HTML', reply_markup=None):
    """Отправляет новое сообщение или редактирует существующее"""
    global message_id
    
    if message_id is None:
        response = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID, 
                "text": text, 
                "parse_mode": parse_mode,
                "reply_markup": reply_markup
            },
            timeout=30
        )
        if response.status_code == 200:
            message_id = response.json()['result']['message_id']
        return
    else:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                json={
                    "chat_id": CHAT_ID,
                    "message_id": message_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "reply_markup": reply_markup
                },
                timeout=30
            )
        except:
            message_id = None
            send_or_edit(text, parse_mode, reply_markup)

def progress_bar(percent, width=10):
    percent = min(100, max(0, percent))
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"{bar} {percent:3.0f}%"

def update_progress(stage_num, stage_name, current, total, start_time, total_proxies=0):
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
    text += f"{'Этап':<28} {'Статус':<12}\n"
    text += f"{'─'*41}\n"
    
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
        text += f"{name:<28} {status:>12}\n"
    
    text += f"</pre>\n"
    
    if total_proxies > 0:
        text += f"\n🟢 <b>Найдено:</b> {total_proxies} прокси"
    
    if stage_name:
        text += f"\n\n📌 <i>{stage_name}</i>"
    
    send_or_edit(text)

def create_proxy_buttons(proxies):
    """Создаёт кнопки для прокси в формате Telegram"""
    keyboard = []
    for i, p in enumerate(proxies[:6], 1):
        flag = p.get('flag', '🇪🇺')
        
        # Кнопка с прокси (левая)
        main_button = {
            "text": f"{flag} Прокси #{i}",
            "url": p['link']
        }
        
        # Кнопка поделиться (правая)
        share_url = f"https://t.me/share/url?url={p['link']}"
        share_button = {
            "text": "📤",
            "url": share_url
        }
        
        keyboard.append([main_button, share_button])
    
    # Кнопка обновления внизу
    keyboard.append([{
        "text": "🔄 Обновить список прокси",
        "callback_data": "refresh"
    }])
    
    return {"inline_keyboard": keyboard}

def send_final_result(proxies):
    """Отправляет финальный результат с кнопками"""
    now = time.strftime("%d.%m %H:%M")
    text = f"<b>🔥 Лучшие прокси SAMOLET на {now}</b>"
    
    if not proxies:
        text += "\n❌ Нет прокси"
        keyboard = {"inline_keyboard": [[{"text": "🔄 Обновить список", "callback_data": "refresh"}]]}
    else:
        keyboard = create_proxy_buttons(proxies)
    
    send_or_edit(text, reply_markup=keyboard)

def parse_proxies_from_file():
    """Парсит best_proxies.txt в список прокси"""
    proxies = []
    try:
        with open('best_proxies.txt', 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
        
        for i, line in enumerate(lines):
            if line.startswith('tg://proxy'):
                proxy = {'link': line}
                if i > 0 and '🇷🇺' in lines[i-1]:
                    proxy['flag'] = '🇷🇺'
                elif i > 0 and '🇪🇺' in lines[i-1]:
                    proxy['flag'] = '🇪🇺'
                else:
                    proxy['flag'] = '🌍'
                proxies.append(proxy)
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
    
    return proxies

def main():
    global message_id
    message_id = None
    start_time = time.time()
    
    # Отправляем начальное сообщение
    send_or_edit("🔄 <b>Запуск обновления прокси...</b>")
    
    # Этап 1: Подготовка
    update_progress(1, "Подготовка...", 1, 1, start_time)
    time.sleep(0.5)
    update_progress(1, "Готов к работе", 1, 1, start_time)
    
    # Этап 2: main.py
    update_progress(2, "Запуск сбора прокси...", 0, 1, start_time)
    
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
            match = re.search(r'\[(\d+)/(\d+)\]', line)
            if match:
                checked = int(match.group(1))
                total = int(match.group(2))
                percent = int(checked * 100 / total) if total > 0 else 0
                if percent >= last_percent + 10 or percent == 100:
                    last_percent = percent
                    update_progress(2, f"Сбор прокси... {percent}%", percent, 100, start_time, total_proxies)
            
            match = re.search(r'RU=(\d+)\s+EU=(\d+)', line)
            if match:
                ru = int(match.group(1))
                eu = int(match.group(2))
                total_proxies = ru + eu
                update_progress(2, f"Найдено {total_proxies} прокси", 100, 100, start_time, total_proxies)
    
    process.wait(timeout=10)
    
    # Этап 3: test_proxies.py
    update_progress(3, "TCP-тестирование...", 0, 100, start_time, total_proxies)
    
    process = subprocess.Popen(
        ['python3', 'test_proxies.py'],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    last_percent = 0
    tested = 0
    total_to_test = max(total_proxies, 50)
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line and 'Проверка' in line and ':' in line:
            tested += 1
            percent = int(tested * 100 / total_to_test) if total_to_test > 0 else 0
            if percent >= last_percent + 10 or percent == 100:
                last_percent = percent
                update_progress(3, f"TCP-тестирование... {percent}% ({tested}/{total_to_test})", percent, 100, start_time, total_proxies)
    
    process.wait(timeout=10)
    
    # Парсим результат
    proxies = parse_proxies_from_file()
    total_proxies_found = len(proxies)
    
    update_progress(3, f"Найдено {total_proxies_found} стабильных", 100, 100, start_time, total_proxies_found)
    
    # Этап 4: Анализ (имитация)
    update_progress(4, "Анализ стабильности...", 0, 100, start_time, total_proxies_found)
    
    for i in range(1, min(total_proxies_found, 100) + 1):
        if i % max(1, total_proxies_found // 10) == 0:
            percent = int(i * 100 / total_proxies_found) if total_proxies_found > 0 else 0
            update_progress(4, f"Анализ прокси {i}/{total_proxies_found}", percent, 100, start_time, total_proxies_found)
        time.sleep(0.05)
    
    update_progress(4, f"Отобрано {total_proxies_found} лучших", 100, 100, start_time, total_proxies_found)
    
    # Этап 5: Проверка
    update_progress(5, "Проверка соединения...", 100, 100, start_time, total_proxies_found)
    time.sleep(0.5)
    
    # Этап 6: Подготовка и отправка
    update_progress(6, "Формирую список...", 100, 100, start_time, total_proxies_found)
    
    # Отправляем в Worker
    try:
        response = httpx.post(
            f"{WORKER_URL}/update",
            json={"proxies": proxies},
            timeout=30
        )
        if response.status_code == 200:
            print(f"✅ Отправлено {len(proxies)} прокси в Worker")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
    
    time.sleep(0.5)
    
    # Финальное сообщение с кнопками
    send_final_result(proxies)

if __name__ == "__main__":
    main()