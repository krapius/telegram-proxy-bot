#!/usr/bin/env python3
"""
Скрипт для отправки прокси из best_proxies.txt в Cloudflare Worker
Запускается после main.py и test_proxies.py
"""

import subprocess
import json
import re
import os
import sys
import httpx

# Конфигурация
WORKER_URL = "https://telegram-proxy-bot.krichencat.workers.dev"
TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_collector():
    """Запускает сборщик прокси"""
    print("\n" + "="*60)
    print("🔄 ЗАПУСК СБОРА ПРОКСИ")
    print("="*60)
    
    # Запускаем main.py
    print("\n1️⃣ Сбор сырых прокси...")
    result = subprocess.run(
        [sys.executable, 'main.py'],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Ошибка main.py: {result.stderr}")
        return False
    
    # Запускаем test_proxies.py
    print("\n2️⃣ Проверка и фильтрация...")
    result = subprocess.run(
        [sys.executable, 'test_proxies.py'],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Ошибка test_proxies.py: {result.stderr}")
        return False
    
    return True

def parse_proxies():
    """Парсит best_proxies.txt в формат для Worker"""
    filename = os.path.join(PROJECT_DIR, "best_proxies.txt")
    if not os.path.exists(filename):
        print(f"⚠️ Файл {filename} не найден")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')
    
    proxies = []
    for i, line in enumerate(lines):
        if line.startswith('tg://proxy'):
            proxy = {'link': line}
            
            # Извлекаем сервер
            server_match = re.search(r'server=([^&]+)', line)
            if server_match:
                proxy['server'] = server_match.group(1)
            
            # Определяем флаг из комментария выше
            if i > 0 and '🇷🇺' in lines[i-1]:
                proxy['flag'] = '🇷🇺'
            elif i > 0 and '🇪🇺' in lines[i-1]:
                proxy['flag'] = '🇪🇺'
            else:
                proxy['flag'] = '🌍'
            
            # Извлекаем тип из комментария
            if i > 0:
                if 'RU' in lines[i-1]:
                    proxy['type'] = '🇷🇺 RU'
                elif 'EU' in lines[i-1]:
                    proxy['type'] = '🇪🇺 EU'
                else:
                    proxy['type'] = '🌍 ALL'
            else:
                proxy['type'] = '🌍 ALL'
            
            proxies.append(proxy)
    
    return proxies

def send_to_worker(proxies):
    """Отправляет прокси в Worker"""
    if not proxies:
        print("❌ Нет прокси для отправки")
        return False
    
    print(f"\n📦 Найдено {len(proxies)} прокси")
    
    try:
        response = httpx.post(
            f"{WORKER_URL}/update",
            json={"proxies": proxies},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Отправлено {data.get('count', 0)} прокси в Worker")
                
                # Проверяем, что записалось
                check_response = httpx.get(WORKER_URL)
                if "Прокси в кэше:" in check_response.text:
                    import re
                    match = re.search(r'Прокси в кэше: (\d+)', check_response.text)
                    if match:
                        print(f"📊 В кэше Worker: {match.group(1)} прокси")
                
                return True
            else:
                print(f"❌ Ошибка: {data}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

def send_test_message():
    """Отправляет тестовое сообщение в Telegram (опционально)"""
    try:
        response = httpx.post(
            f"{WORKER_URL}/bot{TOKEN}/sendMessage",
            json={
                "chat_id": "305673438",  # ваш ID
                "text": "🔄 <b>Прокси обновлены!</b>\n\nНовые прокси доступны по команде /start",
                "parse_mode": "HTML"
            },
            timeout=30
        )
        if response.status_code == 200:
            print("✅ Тестовое сообщение отправлено в Telegram")
    except Exception as e:
        print(f"⚠️ Не удалось отправить тестовое сообщение: {e}")

def main():
    print("="*60)
    print("🤖 ОТПРАВКА ПРОКСИ В CLOUDFLARE WORKER")
    print("="*60)
    print(f"🌐 Worker URL: {WORKER_URL}")
    
    # Запускаем сбор
    if not run_collector():
        print("\n❌ Сбор прокси не удался")
        return 1
    
    # Парсим результат
    proxies = parse_proxies()
    
    if not proxies:
        print("\n❌ Нет прокси для отправки")
        return 1
    
    # Отправляем в Worker
    if send_to_worker(proxies):
        print("\n✅ Прокси успешно обновлены!")
        
        # Опционально: отправляем уведомление в Telegram
        send_test_message()
        
        return 0
    else:
        print("\n❌ Не удалось отправить прокси")
        return 1

if __name__ == "__main__":
    sys.exit(main())