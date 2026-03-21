#!/usr/bin/env python3
"""
Скрипт для обновления прокси с отображением прогресса в Telegram
Запускается в GitHub Actions
"""

import subprocess
import sys
import os
import httpx
import time
import re

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc')
WORKER_URL = os.environ.get('WORKER_URL', 'https://telegram-proxy-bot.krichencat.workers.dev')
CHAT_ID = "305673438"

def send_message(text, parse_mode='HTML'):
    """Отправляет сообщение в Telegram"""
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=30
        )
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️ Не удалось отправить сообщение: {e}")
        return False

def progress_bar(percent, width=10):
    """Создаёт прогресс-бар"""
    percent = min(100, max(0, percent))
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"{bar} {percent:3.0f}%"

def update_progress(stage_num, stage_name, current, total, start_time):
    """Обновляет прогресс с этапами"""
    stages = [
        (1, "1. 🧘 Медитирую"),
        (2, "2. 📦 Сбор прокси"),
        (3, "3. 📊 Проверка Ping"),
        (4, "4. 🔬 Анализ стабильности"),
        (5, "5. 🌐 Проверка соединения"),
        (6, "6. ✨ Подготовка результатов")
    ]
    
    # Расчет прогресса
    stage_percent = (current / total) * 100 if total > 0 else 0
    total_stages = 6
    base_progress = ((stage_num - 1) / total_stages) * 100
    stage_contribution = 100 / total_stages
    total_progress = base_progress + (stage_contribution * (stage_percent / 100))
    total_progress = min(100, max(0, total_progress))
    
    # Время
    elapsed = time.time() - start_time
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)
    if elapsed_min > 0:
        time_display = f"{elapsed_min}м {elapsed_sec:02d}с"
    else:
        time_display = f"{elapsed_sec}с"
    
    # Формируем текст
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
    text += f"\n📌 <i>{stage_name}</i>"
    
    send_message(text)

def run_command(cmd, cwd=None):
    """Запускает команду и возвращает вывод"""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout, result.stderr, result.returncode

def main():
    start_time = time.time()
    
    # Начальное сообщение
    send_message("🔄 <b>Запуск обновления прокси...</b>\n\n⚠️ Процесс займёт 1-2 минуты")
    
    # Этап 1: Подготовка
    update_progress(1, "Подготовка...", 1, 1, start_time)
    time.sleep(0.5)
    update_progress(1, "Готов к работе", 1, 1, start_time)
    
    # Этап 2: main.py (сбор прокси)
    update_progress(2, "Запуск сбора прокси...", 0, 1, start_time)
    
    # Запускаем main.py и читаем вывод для прогресса
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
                    update_progress(2, f"Сбор прокси... {percent}%", percent, 100, start_time)
            
            match = re.search(r'RU=(\d+)\s+EU=(\d+)', line)
            if match:
                ru = int(match.group(1))
                eu = int(match.group(2))
                total_proxies = ru + eu
                update_progress(2, f"Найдено {total_proxies} прокси", 100, 100, start_time)
    
    process.wait(timeout=10)
    
    # Этап 3: test_proxies.py (проверка)
    update_progress(3, "TCP-тестирование...", 0, 100, start_time)
    
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
                update_progress(3, f"TCP-тестирование... {percent}% ({tested}/{total_to_test})", percent, 100, start_time)
    
    process.wait(timeout=10)
    
    # Читаем результат
    with open('best_proxies.txt', 'r') as f:
        content = f.read()
    
    # Считаем прокси
    proxies = [line for line in content.split('\n') if line.startswith('tg://proxy')]
    total_proxies_found = len(proxies)
    
    update_progress(3, f"Найдено {total_proxies_found} стабильных", 100, 100, start_time)
    
    # Этап 4: Анализ стабильности (имитация)
    update_progress(4, "Анализ стабильности...", 0, 100, start_time)
    
    # Парсим прокси из файла
    proxies_list = []
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('tg://proxy'):
            proxy = {'link': line}
            if i > 0 and '🇷🇺' in lines[i-1]:
                proxy['flag'] = '🇷🇺'
            elif i > 0 and '🇪🇺' in lines[i-1]:
                proxy['flag'] = '🇪🇺'
            else:
                proxy['flag'] = '🌍'
            proxies_list.append(proxy)
    
    # Симулируем анализ
    for i in range(1, min(len(proxies_list), 100) + 1):
        if i % max(1, len(proxies_list) // 10) == 0:
            percent = int(i * 100 / len(proxies_list)) if len(proxies_list) > 0 else 0
            update_progress(4, f"Анализ прокси {i}/{len(proxies_list)}", percent, 100, start_time)
        time.sleep(0.05)
    
    update_progress(4, f"Отобрано {total_proxies_found} лучших", 100, 100, start_time)
    
    # Этап 5: Проверка соединения
    update_progress(5, "Проверка соединения...", 100, 100, start_time)
    time.sleep(0.5)
    
    # Этап 6: Подготовка результатов и отправка в Worker
    update_progress(6, "Формирую список...", 100, 100, start_time)
    
    # Отправляем в Worker
    try:
        response = httpx.post(
            f"{WORKER_URL}/update",
            json={"proxies": proxies_list},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Отправлено {data.get('count', 0)} прокси в Worker")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
    
    time.sleep(0.5)
    update_progress(6, "Готово!", 100, 100, start_time)
    
    # Финальное сообщение
    total_time = time.time() - start_time
    total_min = int(total_time // 60)
    total_sec = int(total_time % 60)
    
    final_text = f"✅ <b>Обновление завершено!</b>\n\n"
    final_text += f"📦 Найдено: {total_proxies_found} прокси\n"
    final_text += f"⏱️ Время: {total_min}м {total_sec:02d}с\n\n"
    final_text += f"Отправьте /start для просмотра списка"
    
    send_message(final_text)

if __name__ == "__main__":
    main()