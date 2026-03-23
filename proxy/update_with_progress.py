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

# def send_final_result(proxies):
#     """Отправляет финальный результат с пингом и скоростью"""
#     now = time.strftime("%d.%m %H:%M")
#     text = f"<b>🔥 Лучшие прокси SAMOLET на {now}</b>\n\n"
    
#     if not proxies:
#         text += "❌ Нет прокси"
#         keyboard = {"inline_keyboard": [[{"text": "🔄 Обновить список", "callback_data": "refresh"}]]}
#         send_message(text, reply_markup=keyboard)
#         return
    
#     for i, p in enumerate(proxies[:6], 1):
#         flag = p.get('flag', '🇪🇺')
#         stats = p.get('strict_stats', {})
#         ping = stats.get('ping', p.get('ping', 0))
#         speed = p.get('download_speed', 0)
        
#         # Определяем качество по пингу
#         if ping and ping < 100:
#             quality = "🚀"
#         elif ping and ping < 200:
#             quality = "✅"
#         elif ping:
#             quality = "⚠️"
#         else:
#             quality = "❓"
        
#         if ping and speed:
#             text += f"{flag} {quality} <b>Прокси #{i}</b> — {ping:.0f}мс | {speed:.0f} КБ/с\n"
#         elif ping:
#             text += f"{flag} {quality} <b>Прокси #{i}</b> — {ping:.0f}мс\n"
#         else:
#             text += f"{flag} {quality} <b>Прокси #{i}</b>\n"
#         text += f"<code>{p['link']}</code>\n\n"
    
#     text += f"\n🔄 <i>Обновляется автоматически каждые 6 часов</i>"
#     text += f"\n📊 <i>🚀 &lt;100мс — отлично | ✅ 100-200мс — хорошо | ⚠️ &gt;200мс — медленно</i>"
    
#     keyboard = create_proxy_buttons(proxies[:10])
#     send_message(text, reply_markup=keyboard)


def parse_proxies_from_file():
    """Парсит best_proxies.json в список прокси с пингом и скоростью, фильтруя невалидные"""
    proxies = []
    try:
        # Сначала пробуем читать JSON
        with open('best_proxies.json', 'r', encoding='utf-8') as f:
            proxies = json.load(f)
            print(f"📦 Загружено {len(proxies)} прокси из JSON")
            
            # Фильтруем невалидные ссылки
            valid_proxies = []
            for p in proxies:
                link = p.get('link', '')
                # Проверяем на невалидные символы
                if 'server=' in link:
                    server = link.split('server=')[1].split('&')[0]
                    # Пропускаем ссылки с точкой в конце
                    if server.endswith('.'):
                        print(f"⚠️ Пропускаем невалидную ссылку: {server}")
                        continue
                valid_proxies.append(p)
            
            print(f"📦 После фильтрации: {len(valid_proxies)} прокси")
            return valid_proxies
    except:
        pass
    
    # Если JSON нет, читаем txt (старый формат)
    try:
        with open('best_proxies.txt', 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
        
        for i, line in enumerate(lines):
            if line.startswith('tg://proxy'):
                # Проверяем на невалидные ссылки
                server_match = re.search(r'server=([^&]+)', line)
                if server_match:
                    server = server_match.group(1)
                    # Пропускаем ссылки с пробелами или точкой в конце
                    if ' ' in server or server.endswith('.'):
                        print(f"⚠️ Пропускаем невалидную ссылку: {line[:80]}...")
                        continue
                
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
    
    print(f"📦 Найдено {len(proxies)} прокси в файле")
    return proxies

def main():
    start_time = time.time()
    
    print("🔄 Запуск обновления прокси...")
    
    # Отправляем начальное сообщение (будет удалено через 2 секунды)
    start_message_id = send_message("🔄 <b>Обновление прокси начато!</b>\n\nЭто займёт 1-2 минуты...\nРезультат появится здесь автоматически.")
    
    # Небольшая пауза, чтобы сообщение успело отобразиться
    time.sleep(0.1)
    
    # Отправляем сообщение с прогрессом
    progress_message_id = send_message("🔄 <b>Запуск обновления прокси...</b>")
    if not progress_message_id:
        print("❌ Не удалось отправить начальное сообщение")
        return
    
    # Удаляем стартовое сообщение
    if start_message_id:
        delete_message(start_message_id)
    
    # Этап 1: Подготовка
    update_progress(progress_message_id, 1, "Подготовка...", 1, 1, start_time)
    time.sleep(0.5)
    update_progress(progress_message_id, 1, "Готов к работе", 1, 1, start_time)
    
    # Этап 2: main.py
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
    
    # Этап 3: test_proxies.py
    print("📊 Запуск test_proxies.py...")
    update_progress(progress_message_id, 3, "TCP-тестирование...", 0, 100, start_time, total_proxies)
    
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
                update_progress(progress_message_id, 3, f"TCP-тестирование... {percent}% ({tested}/{total_to_test})", percent, 100, start_time, total_proxies)
    
    process.wait(timeout=10)
    print("✅ test_proxies.py завершён")
    
    # Парсим результат
    proxies = parse_proxies_from_file()
    total_proxies_found = len(proxies)
    
    update_progress(progress_message_id, 3, f"Найдено {total_proxies_found} стабильных", 100, 100, start_time, total_proxies_found)
    
    # Этап 4: Анализ (имитация)
    update_progress(progress_message_id, 4, "Анализ стабильности...", 0, 100, start_time, total_proxies_found)
    
    for i in range(1, min(total_proxies_found, 100) + 1):
        if i % max(1, total_proxies_found // 10) == 0:
            percent = int(i * 100 / total_proxies_found) if total_proxies_found > 0 else 0
            update_progress(progress_message_id, 4, f"Анализ прокси {i}/{total_proxies_found}", percent, 100, start_time, total_proxies_found)
        time.sleep(0.05)
    
    update_progress(progress_message_id, 4, f"Отобрано {total_proxies_found} лучших", 100, 100, start_time, total_proxies_found)
    
    # Этап 5: Проверка
    update_progress(progress_message_id, 5, "Проверка соединения...", 100, 100, start_time, total_proxies_found)
    time.sleep(1)
    
    # Этап 6: Подготовка и отправка
    update_progress(progress_message_id, 6, "Формирую список...", 100, 100, start_time, total_proxies_found)
    
    # Отправляем в Worker
    print(f"📤 Отправка {len(proxies)} прокси в Worker...")
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
    
    # Удаляем сообщение с прогрессом
    delete_message(progress_message_id)
    
    # Отправляем финальный результат
    # send_final_result(proxies)
    print("🎉 Обновление завершено!")

if __name__ == "__main__":
    main()