#!/usr/bin/env python3
import httpx
import json
import re
import sys
import os

WORKER_URL = os.environ.get('WORKER_URL', 'https://telegram-proxy-bot.krichencat.workers.dev')

def parse_proxies():
    proxies = []
    filename = 'best_proxies.txt'
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')
    
    print(f"📄 Прочитано {len(lines)} строк")
    
    for i, line in enumerate(lines):
        if line.startswith('tg://proxy'):
            proxy = {'link': line}
            server_match = re.search(r'server=([^&]+)', line)
            if server_match:
                proxy['server'] = server_match.group(1)
            if i > 0 and '🇷🇺' in lines[i-1]:
                proxy['flag'] = '🇷🇺'
            elif i > 0 and '🇪🇺' in lines[i-1]:
                proxy['flag'] = '🇪🇺'
            else:
                proxy['flag'] = '🌍'
            proxies.append(proxy)
    
    print(f"📦 Найдено {len(proxies)} прокси")
    return proxies

def send_to_worker(proxies):
    if not proxies:
        print("❌ Нет прокси для отправки")
        return False
    
    try:
        response = httpx.post(
            f"{WORKER_URL}/update",
            json={"proxies": proxies},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Успешно! Отправлено {data.get('count', 0)} прокси")
                return True
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    proxies = parse_proxies()
    if proxies:
        success = send_to_worker(proxies)
        sys.exit(0 if success else 1)
    else:
        print("⚠️ Нет прокси для отправки")
        sys.exit(1)
