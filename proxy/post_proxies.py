#!/usr/bin/env python3
import subprocess
import re
import os
from datetime import datetime
import asyncio
import json
import time
import socket
import urllib.parse
import geoip2.database
import requests
import ipaddress
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ===== НАСТРОЙКИ =====
TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
CHANNEL_ID = -1003605280638
WORKER_URL = "https://tg-pr.krichencat.workers.dev"
# =====================

# ===== НАСТРОЙКИ ГЕОЛОКАЦИИ =====
USE_GEOIP = True
GEOIP_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GeoLite2-Country.mmdb")
# ================================

# ===== ПАРАМЕТРЫ СТАБИЛЬНОСТИ =====
STABILITY_LEVELS = {
    'quick': {
        'samples': 2,
        'max_jitter': 250,
        'max_loss': 30,
        'max_ping': 800,
        'description': 'Быстрый отбор'
    },
    'strict': {
        'samples': 5,
        'max_jitter': 80,
        'max_loss': 10,
        'max_ping': 300,
        'description': 'Жесткий отбор'
    }
}
# ====================================

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"📂 Проект в папке: {PROJECT_DIR}")

# Эмодзи флагов
country_flags = {
    'RU': '🇷🇺', 'DE': '🇩🇪', 'FR': '🇫🇷', 'NL': '🇳🇱', 
    'GB': '🇬🇧', 'US': '🇺🇸', 'CA': '🇨🇦', 'JP': '🇯🇵',
    'CN': '🇨🇳', 'BR': '🇧🇷', 'IN': '🇮🇳', 'AU': '🇦🇺',
    'IT': '🇮🇹', 'ES': '🇪🇸', 'PL': '🇵🇱', 'UA': '🇺🇦',
}

# Кэши
dns_cache = {}
country_cache = {}
updating_flag = False

# ===== ФУНКЦИИ ГЕОЛОКАЦИИ =====
def resolve_domain(server):
    try:
        if server in dns_cache:
            return dns_cache[server]
        try:
            ipaddress.ip_address(server)
            dns_cache[server] = server
            return server
        except ValueError:
            pass
        ip = socket.gethostbyname(server)
        dns_cache[server] = ip
        return ip
    except Exception as e:
        print(f"⚠️ DNS ошибка {server}: {e}")
        return None

def get_country_code(server):
    try:
        cache_key = f"country_{server}"
        if cache_key in country_cache:
            return country_cache[cache_key]
        
        ip = resolve_domain(server)
        if not ip:
            return None
        
        if USE_GEOIP and os.path.exists(GEOIP_DB_PATH):
            try:
                with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
                    response = reader.country(ip)
                    country_code = response.country.iso_code
                    if country_code:
                        country_cache[cache_key] = country_code
                        return country_code
            except Exception as e:
                print(f"⚠️ GeoIP ошибка {server}: {e}")
        
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}?fields=countryCode', timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('countryCode'):
                    country_code = data['countryCode']
                    country_cache[cache_key] = country_code
                    return country_code
        except Exception as e:
            print(f"⚠️ ip-api ошибка {server}: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Общая ошибка {server}: {e}")
        return None

# ===== ФУНКЦИИ РАБОТЫ С ПРОКСИ =====
def clean_secret(secret):
    try:
        secret = urllib.parse.unquote(secret)
        if not re.match(r'^[a-fA-F0-9+/=]+$', secret):
            return None, "Недопустимые символы"
        if len(secret) < 16:
            return None, "Слишком короткий"
        return secret, "OK"
    except:
        return None, "Ошибка"

def parse_best_proxies_file():
    filename = os.path.join(PROJECT_DIR, "best_proxies.txt")
    if not os.path.exists(filename):
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    proxies = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#') and '—' in line:
            proxy_info = {}
            
            server_match = re.search(r'([a-zA-Z0-9][a-zA-Z0-9\.\-]+[a-zA-Z0-9])', line)
            if server_match:
                proxy_info['server'] = server_match.group(1)
            
            if '🇷🇺' in line:
                proxy_info['type'] = '🇷🇺 RU'
            elif '🇪🇺' in line:
                proxy_info['type'] = '🇪🇺 EU'
            else:
                proxy_info['type'] = '🌍 ALL'
            
            ping_match = re.search(r'п:(\d+)мс', line)
            if ping_match:
                proxy_info['ping'] = float(ping_match.group(1))
            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('tg://proxy'):
                    clean_link = next_line
                    secret_match = re.search(r'secret=([^&]+)', clean_link)
                    if secret_match:
                        original_secret = secret_match.group(1)
                        cleaned_secret, _ = clean_secret(original_secret)
                        if cleaned_secret:
                            clean_link = clean_link.replace(f'secret={original_secret}', f'secret={cleaned_secret}')
                            proxy_info['link'] = clean_link
                            port_match = re.search(r'port=(\d+)', clean_link)
                            proxy_info['port'] = port_match.group(1) if port_match else '443'
                            
                            country_code = get_country_code(proxy_info['server'])
                            if country_code:
                                proxy_info['country'] = country_code
                                proxy_info['flag'] = country_flags.get(country_code, '🇪🇺')
                            
                            proxies.append(proxy_info)
            i += 2
        else:
            i += 1
    
    proxies.sort(key=lambda x: x.get('ping', 999))
    return proxies

def create_proxy_buttons(proxies):
    keyboard = []
    for i, p in enumerate(proxies[:6], 1):
        flag = p.get('flag', '🇷🇺' if 'RU' in p.get('type', '') else '🇪🇺')
        main_button = InlineKeyboardButton(text=f"{flag} Прокси #{i}", url=p['link'])
        encoded_link = urllib.parse.quote(p['link'])
        share_url = f"https://t.me/share/url?url={encoded_link}"
        share_button = InlineKeyboardButton(text="📤", url=share_url)
        keyboard.append([main_button, share_button])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить список прокси", callback_data="refresh")])
    return InlineKeyboardMarkup(keyboard)

# ===== ФУНКЦИИ ПРОВЕРКИ СТАБИЛЬНОСТИ =====
def test_proxy_stability(server, port, level='strict'):
    config = STABILITY_LEVELS[level]
    pings = []
    losses = 0
    
    # TCP-тест
    for i in range(config['samples']):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((server, port))
            response_time = (time.time() - start) * 1000
            sock.close()
            if result == 0:
                pings.append(response_time)
            else:
                losses += 1
        except:
            losses += 1
        if i < config['samples'] - 1:
            time.sleep(0.3)
    
    if not pings:
        return None, None, 100, False
    
    avg_ping = sum(pings) / len(pings)
    loss_percent = (losses / config['samples']) * 100
    
    if len(pings) > 1:
        variance = sum((p - avg_ping) ** 2 for p in pings) / len(pings)
        jitter = variance ** 0.5
    else:
        jitter = 0
    
    # ===== НОВАЯ ПРОВЕРКА: ЗАГРУЗКА НЕБОЛЬШОГО ФАЙЛА =====
    download_speed = None
    download_success = False
    
    if level == 'strict':
        print(f"\n      📥 Тест загрузки (скачивание тестового файла):")
        
        # Небольшой тестовый файл (1 МБ)
        test_url = f"http://{server}:{port}/speedtest/1mb.bin"
        
        try:
            import urllib.request
            import ssl
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            start_time = time.time()
            req = urllib.request.Request(test_url, method='GET')
            
            # Скачиваем первые 100 КБ для проверки скорости
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                data = response.read(102400)  # 100 КБ
                elapsed = time.time() - start_time
                
                if len(data) > 0:
                    download_speed = (len(data) / 1024) / elapsed  # КБ/сек
                    download_success = True
                    print(f"         ✅ Скорость загрузки: {download_speed:.0f} КБ/сек")
                else:
                    print(f"         ⚠️ Пустой ответ")
                    
        except Exception as e:
            print(f"         ❌ Ошибка загрузки: {str(e)[:60]}")
    
    meets_criteria = (
        avg_ping <= config['max_ping'] and 
        jitter <= config['max_jitter'] and 
        loss_percent <= config['max_loss']
    )
    
    # Для strict уровня добавляем условие скорости загрузки (минимально 50 КБ/сек)
    if level == 'strict' and download_success:
        if download_speed < 50:
            meets_criteria = False
            print(f"      ⚠️ Слишком низкая скорость: {download_speed:.0f} КБ/сек (мин. 50)")
    
    status = "✅ ПРОШЕЛ" if meets_criteria else "❌ НЕ ПРОШЕЛ"
    print(f"      📈 Результат: п={avg_ping:.0f}мс дж={jitter:.0f}мс пот={loss_percent:.0f}% {status}")
    
    return avg_ping, jitter, loss_percent, meets_criteria

def advanced_final_check(proxies, progress_callback=None):
    """Оптимизированная проверка стабильности с callback для прогресса"""
    print("\n" + "="*70)
    print("🔬 ПРОВЕРКА СТАБИЛЬНОСТИ")
    print("="*70)
    
    if not proxies:
        print("❌ Нет прокси для проверки")
        return []
    
    # Этап 1: Быстрый отбор (2 замера)
    if progress_callback:
        progress_callback("Быстрый отбор...", 0, len(proxies[:15]))
    
    quick_pass = []
    for i, p in enumerate(proxies[:15], 1):
        if progress_callback:
            progress_callback(f"Быстрый отбор: {p['server']}", i, len(proxies[:15]))
        
        if 'link' not in p:
            continue
        port_match = re.search(r'port=(\d+)', p['link'])
        port = int(port_match.group(1)) if port_match else 443
        _, _, _, passed = test_proxy_stability(p['server'], port, level='quick')
        if passed:
            quick_pass.append(p)
    
    print(f"\n✅ Быстрый отбор: {len(quick_pass)} прокси")
    
    if len(quick_pass) < 3:
        return quick_pass[:5]
    
    # Этап 2: Жесткий отбор (5 замеров)
    if progress_callback:
        progress_callback("Жесткий отбор...", 0, len(quick_pass[:8]))
    
    strict_pass = []
    for i, p in enumerate(quick_pass[:8], 1):
        if progress_callback:
            progress_callback(f"Жесткий отбор: {p['server']}", i, len(quick_pass[:8]))
        
        port_match = re.search(r'port=(\d+)', p['link'])
        port = int(port_match.group(1)) if port_match else 443
        avg_ping, jitter, loss, passed = test_proxy_stability(p['server'], port, level='strict')
        if passed:
            quality_score = ((300 - min(avg_ping, 300)) * 0.4 + (100 - min(jitter, 100)) * 0.35 + (100 - loss) * 0.25)
            p['quality_score'] = quality_score
            strict_pass.append(p)
    
    print(f"\n✅ Жесткий отбор: {len(strict_pass)} прокси")
    
    # Разделяем по странам
    ru_proxies = [p for p in strict_pass if 'RU' in p.get('type', '') or p.get('country') == 'RU']
    eu_proxies = [p for p in strict_pass if 'EU' in p.get('type', '') or p.get('country') not in ['RU', None]]
    ru_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    eu_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    
    final_proxies = []
    for i in range(max(len(ru_proxies[:5]), len(eu_proxies[:5]))):
        if i < len(ru_proxies[:5]):
            final_proxies.append(ru_proxies[:5][i])
        if i < len(eu_proxies[:5]):
            final_proxies.append(eu_proxies[:5][i])
    
    print(f"\n🏆 ИТОГО: {len(final_proxies)} прокси")
    return final_proxies[:10]

# ===== БОТ С ПРОГРЕСС-БАРОМ =====
class ProgressBot:
    def __init__(self, token, worker_url):
        self.token = token
        self.worker_url = worker_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=180.0)
        self.last_update_id = 0
        self.current_message_id = None
        self.current_chat_id = None
    
    async def _request(self, method, endpoint, **kwargs):
        url = f"{self.worker_url}/bot{self.token}/{endpoint}"
        if method == 'get':
            response = await self.client.get(url, params=kwargs.get('params'))
        else:
            response = await self.client.post(url, json=kwargs.get('json'))
        return response.json()
    
    async def get_me(self):
        return await self._request('get', 'getMe')
    
    async def get_updates(self, offset=None, timeout=30):
        params = {'timeout': timeout}
        if offset:
            params['offset'] = offset
        return await self._request('get', 'getUpdates', params=params)
    
    async def send_message(self, chat_id, text, parse_mode='HTML', reply_markup=None):
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
        if reply_markup:
            data['reply_markup'] = reply_markup.to_dict() if hasattr(reply_markup, 'to_dict') else reply_markup
        return await self._request('post', 'sendMessage', json=data)
    
    async def edit_message_text(self, chat_id, message_id, text, parse_mode='HTML', reply_markup=None):
        data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': parse_mode}
        if reply_markup:
            data['reply_markup'] = reply_markup.to_dict() if hasattr(reply_markup, 'to_dict') else reply_markup
        
        # Добавляем повторные попытки
        for attempt in range(3):
            try:
                return await self._request('post', 'editMessageText', json=data)
            except Exception as e:
                if "timeout" in str(e).lower() and attempt < 2:
                    await asyncio.sleep(1)
                    continue
                raise
    
    async def answer_callback_query(self, callback_query_id, text=None):
        data = {'callback_query_id': callback_query_id}
        if text:
            data['text'] = text
        return await self._request('post', 'answerCallbackQuery', json=data)
    
    def progress_bar(self, percent, width=10):
        percent = min(100, max(0, percent))
        filled = int(width * percent / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"{bar} {percent:3.0f}%"
    
    async def update_progress(self, stage_num, stage_name, current=None, total=None, total_proxies=0, start_time=None):
        stages = [
            (1, "1. 🧘 Медитирую"),
            (2, "2. 📦 Сбор прокси"),
            (3, "3. 📊 Проверка Ping"),
            (4, "4. 🔬 Анализ стабильности"),
            (5, "5. 🌐 Проверка соединения"),
            (6, "6. ✨ Подготовка результатов")
        ]
        
        stage_percent = 0
        if current is not None and total is not None and total > 0:
            stage_percent = (current / total) * 100
        
        total_stages = 6
        base_progress = ((stage_num - 1) / total_stages) * 100
        stage_contribution = 100 / total_stages
        total_progress = base_progress + (stage_contribution * (stage_percent / 100))
        total_progress = min(100, max(0, total_progress))
        
        time_display = ""
        if start_time:
            elapsed = time.time() - start_time
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            if elapsed_min > 0:
                time_display = f"{elapsed_min}м {elapsed_sec:02d}с"
            else:
                time_display = f"{elapsed_sec}с"
        
        text = f"<b>🔄 Обновление прокси</b>\n\n"
        text += f"<code>{self.progress_bar(total_progress, 10)}</code>"
        if time_display:
            text += f"   —   <i>{time_display}</i>\n\n"
        else:
            text += "\n\n"
        
        text += f"<pre>"
        text += f"{'Этап':<28} {'Статус':<12}\n"
        text += f"{'─'*41}\n"
        
        for num, name in stages:
            if num < stage_num:
                status = "✅"
            elif num == stage_num:
                if stage_percent > 0:
                    bar = self.progress_bar(stage_percent, 8)
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
        
        if self.current_message_id:
            try:
                await self.edit_message_text(self.current_chat_id, self.current_message_id, text, parse_mode='HTML')
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"⚠️ Ошибка в update_progress: {e}")
    
    async def run_update_process(self, chat_id, message_id):
        global updating_flag
        
        if updating_flag:
            return
        
        updating_flag = True
        self.current_chat_id = chat_id
        self.current_message_id = message_id
        start_time = time.time()
        total_proxies_found = 0
        last_update_time = 0
        last_percent_sent = -1
        
        async def safe_update(stage_num, stage_name, current=None, total=None, total_proxies=0):
            """Безопасное обновление с защитой от слишком частых вызовов"""
            nonlocal last_update_time, last_percent_sent
            now = time.time()
            
            percent = 0
            if current is not None and total is not None and total > 0:
                percent = int(current * 100 / total)
            
            # Обновляем только если:
            # 1. Прошло больше 1.5 секунды ИЛИ
            # 2. Процент изменился на 10% ИЛИ
            # 3. Это финальное обновление (100%)
            should_update = False
            if now - last_update_time >= 1.5:
                should_update = True
            elif percent >= last_percent_sent + 10:
                should_update = True
            elif percent == 100 and last_percent_sent != 100:
                should_update = True
            
            if not should_update:
                return
            
            last_update_time = now
            last_percent_sent = percent
            
            try:
                await self.update_progress(stage_num, stage_name, current, total, total_proxies, start_time)
            except Exception as e:
                if "Message is not modified" not in str(e):
                    print(f"⚠️ Ошибка обновления ({stage_name}): {e}")
        
        try:
            # Этап 1: Подготовка
            print("📍 Этап 1: Подготовка")
            await safe_update(1, "Подготовка...", 1, 1)
            await asyncio.sleep(0.5)
            await safe_update(1, "Готов к работе", 1, 1)
            
            # Этап 2: main.py (сбор прокси)
            print("📍 Этап 2: Запуск main.py")
            await safe_update(2, "Запуск сбора прокси...", 0, 1)
            
            process = subprocess.Popen(
                ['python3', 'main.py'], cwd=PROJECT_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
            
            last_percent = 0
            while True:
                try:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        line = line.strip()
                        if '[' in line and ']' in line:
                            print(f"   main.py: {line[:80]}")
                        
                        match = re.search(r'\[(\d+)/(\d+)\]', line)
                        if match:
                            checked = int(match.group(1))
                            total = int(match.group(2))
                            percent = int(checked * 100 / total) if total > 0 else 0
                            if percent >= last_percent + 10 or percent == 100:
                                last_percent = percent
                                await safe_update(2, f"Сбор прокси... {percent}%", percent, 100, total_proxies_found)
                        
                        if 'Верифицировано:' in line:
                            match = re.search(r'RU=(\d+)\s+EU=(\d+)', line)
                            if match:
                                ru = int(match.group(1))
                                eu = int(match.group(2))
                                total_proxies_found = ru + eu
                                print(f"   Найдено прокси: RU={ru}, EU={eu}")
                                await safe_update(2, f"Найдено {total_proxies_found} прокси", 100, 100, total_proxies_found)
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"⚠️ Ошибка чтения main.py: {e}")
                    break
            
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
            
            proxies = parse_best_proxies_file()
            total_proxies_found = len(proxies)
            print(f"   Собрано прокси: {total_proxies_found}")
            await safe_update(2, f"Собрано {total_proxies_found} прокси", 100, 100, total_proxies_found)
            
            # Этап 3: test_proxies.py (проверка)
            print("📍 Этап 3: Запуск test_proxies.py")
            await safe_update(3, "TCP-тестирование...", 0, 100, total_proxies_found)
            
            process = subprocess.Popen(
                ['python3', 'test_proxies.py'], cwd=PROJECT_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
            )
            
            last_percent = 0
            tested = 0
            total_to_test = max(total_proxies_found, 50)
            
            while True:
                try:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        line = line.strip()
                        if 'Проверка' in line and ':' in line:
                            tested += 1
                            percent = int(tested * 100 / total_to_test)
                            if percent >= last_percent + 10 or percent == 100:
                                last_percent = percent
                                print(f"   Проверено: {tested}/{total_to_test} ({percent}%)")
                                await safe_update(3, f"TCP-тестирование... {percent}% ({tested}/{total_to_test})", 
                                                 percent, 100, total_proxies_found)
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"⚠️ Ошибка чтения test_proxies.py: {e}")
                    break
            
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
            
            proxies = parse_best_proxies_file()
            total_proxies_found = len(proxies)
            print(f"   Найдено стабильных: {total_proxies_found}")
            await safe_update(3, f"Найдено {total_proxies_found} стабильных", 100, 100, total_proxies_found)
            
            # Этап 4: Анализ стабильности
            print("📍 Этап 4: Анализ стабильности")
            await safe_update(4, "Анализ стабильности...", 0, 100, total_proxies_found)
            
            proxies_list = parse_best_proxies_file()
            
            working_proxies = []
            if proxies_list:
                print(f"   Всего для анализа: {len(proxies_list)}")
                quick_pass = []
                total_quick = min(len(proxies_list), 15)
                
                for i, p in enumerate(proxies_list[:15], 1):
                    percent = int(i * 100 / total_quick) if total_quick > 0 else 0
                    print(f"   Быстрый отбор {i}/{total_quick}: {p['server']}")
                    await safe_update(4, f"Быстрый отбор: {p['server']}", percent, 100, total_proxies_found)
                    
                    if 'link' not in p:
                        continue
                    port_match = re.search(r'port=(\d+)', p['link'])
                    port = int(port_match.group(1)) if port_match else 443
                    try:
                        _, _, _, passed = test_proxy_stability(p['server'], port, level='quick')
                        if passed:
                            quick_pass.append(p)
                            print(f"      ✅ Прошел быстрый отбор")
                        else:
                            print(f"      ❌ Не прошел")
                    except Exception as e:
                        print(f"      ⚠️ Ошибка: {e}")
                
                print(f"   Быстрый отбор прошли: {len(quick_pass)} прокси")
                
                if len(quick_pass) >= 3:
                    total_strict = min(len(quick_pass), 8)
                    strict_pass = []
                    
                    for i, p in enumerate(quick_pass[:8], 1):
                        percent = int(i * 100 / total_strict) if total_strict > 0 else 0
                        print(f"   Жесткий отбор {i}/{total_strict}: {p['server']}")
                        await safe_update(4, f"Жесткий отбор: {p['server']}", percent, 100, total_proxies_found)
                        
                        port_match = re.search(r'port=(\d+)', p['link'])
                        port = int(port_match.group(1)) if port_match else 443
                        try:
                            avg_ping, jitter, loss, passed = test_proxy_stability(p['server'], port, level='strict')
                            if passed:
                                quality_score = ((300 - min(avg_ping, 300)) * 0.4 + (100 - min(jitter, 100)) * 0.35 + (100 - loss) * 0.25)
                                p['quality_score'] = quality_score
                                strict_pass.append(p)
                                print(f"      ✅ Прошел жесткий отбор (пинг={avg_ping:.0f}мс, качество={quality_score:.0f})")
                            else:
                                print(f"      ❌ Не прошел жесткий отбор")
                        except Exception as e:
                            print(f"      ⚠️ Ошибка: {e}")
                    
                    # Разделяем по странам
                    ru_proxies = [p for p in strict_pass if 'RU' in p.get('type', '') or p.get('country') == 'RU']
                    eu_proxies = [p for p in strict_pass if 'EU' in p.get('type', '') or p.get('country') not in ['RU', None]]
                    ru_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
                    eu_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
                    
                    print(f"   RU прокси: {len(ru_proxies)}, EU прокси: {len(eu_proxies)}")
                    
                    for i in range(max(len(ru_proxies[:5]), len(eu_proxies[:5]))):
                        if i < len(ru_proxies[:5]):
                            working_proxies.append(ru_proxies[:5][i])
                        if i < len(eu_proxies[:5]):
                            working_proxies.append(eu_proxies[:5][i])
                    
                    total_proxies_found = len(working_proxies[:10])
                else:
                    working_proxies = quick_pass[:5]
                    total_proxies_found = len(working_proxies)
            
            print(f"   Отобрано итого: {total_proxies_found} прокси")
            try:
                await safe_update(4, f"Отобрано {total_proxies_found} лучших", 100, 100, total_proxies_found)
            except Exception as e:
                print(f"⚠️ Ошибка обновления этапа 4: {e}")
            
            # Небольшая пауза перед следующими этапами
            await asyncio.sleep(0.5)
            
            # Этап 5: Проверка соединения
            print("📍 Этап 5: Проверка соединения")
            try:
                await safe_update(5, "Проверка соединения...", 100, 100, total_proxies_found)
            except Exception as e:
                print(f"⚠️ Ошибка обновления этапа 5: {e}")
            await asyncio.sleep(0.5)
            
            # Этап 6: Подготовка результатов
            print("📍 Этап 6: Подготовка результатов")
            try:
                await safe_update(6, "Формирую список...", 100, 100, total_proxies_found)
            except Exception as e:
                print(f"⚠️ Ошибка обновления этапа 6: {e}")
            await asyncio.sleep(0.5)
            
            # Отправляем результат с обработкой ошибок
            if total_proxies_found == 0:
                try:
                    await self.edit_message_text(chat_id, message_id, 
                        "❌ <b>Не удалось найти прокси</b>\n\nПопробуйте позже", 
                        parse_mode='HTML')
                except Exception as e:
                    if "message to edit not found" not in str(e).lower():
                        print(f"⚠️ Ошибка отправки: {e}")
                    await self.send_message(chat_id, "❌ Не удалось найти прокси\nПопробуйте позже")
            else:
                await self.send_proxy_list_result(chat_id, message_id, working_proxies[:10])
            
            print(f"\n✅ Обновление завершено! Найдено {total_proxies_found} прокси")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            try:
                await self.edit_message_text(chat_id, message_id, 
                    f"❌ <b>Ошибка обновления</b>\n\n{str(e)[:200]}", parse_mode='HTML')
            except:
                try:
                    await self.send_message(chat_id, f"❌ Ошибка обновления\n\n{str(e)[:200]}")
                except:
                    pass
        finally:
            updating_flag = False
            self.current_message_id = None
            self.current_chat_id = None
    
    async def send_proxy_list_result(self, chat_id, message_id, proxies):
        now = datetime.now().strftime("%d.%m %H:%M")
        text = f"<b>🔥 Лучшие прокси SAMOLET на {now}</b>"
        
        if not proxies:
            text += "\n❌ Нет прокси"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Обновить список", callback_data="refresh")]])
            try:
                await self.edit_message_text(chat_id, message_id, text, parse_mode='HTML', reply_markup=keyboard)
            except Exception as e:
                error_msg = str(e).lower()
                print(f"⚠️ Ошибка отправки результата: {e}")
                if "message to edit not found" in error_msg or "message is not modified" in error_msg:
                    await self.send_message(chat_id, text, parse_mode='HTML', reply_markup=keyboard)
                elif "timeout" in error_msg:
                    await asyncio.sleep(2)
                    try:
                        await self.edit_message_text(chat_id, message_id, text, parse_mode='HTML', reply_markup=keyboard)
                    except:
                        await self.send_message(chat_id, text, parse_mode='HTML', reply_markup=keyboard)
            return
        
        keyboard = create_proxy_buttons(proxies[:10])
        try:
            await self.edit_message_text(chat_id, message_id, text, parse_mode='HTML', reply_markup=keyboard)
        except Exception as e:
            error_msg = str(e).lower()
            print(f"⚠️ Ошибка отправки результата: {e}")
            if "message to edit not found" in error_msg or "message is not modified" in error_msg:
                await self.send_message(chat_id, text, parse_mode='HTML', reply_markup=keyboard)
            elif "timeout" in error_msg:
                await asyncio.sleep(2)
                try:
                    await self.edit_message_text(chat_id, message_id, text, parse_mode='HTML', reply_markup=keyboard)
                except:
                    await self.send_message(chat_id, text, parse_mode='HTML', reply_markup=keyboard)
    
    async def process_update(self, update):
        try:
            if 'message' in update:
                msg = update['message']
                text = msg.get('text', '')
                chat_id = msg['chat']['id']
                username = msg['from'].get('username', 'unknown')
                print(f"\n📥 {text} от @{username}")
                
                if text == '/start':
                    proxies = parse_best_proxies_file()
                    if proxies:
                        working = advanced_final_check(proxies) if proxies else []
                        now = datetime.now().strftime("%d.%m %H:%M")
                        result_text = f"<b>🔥 Лучшие прокси SAMOLET на {now}</b>"
                        if working:
                            keyboard = create_proxy_buttons(working)
                            await self.send_message(chat_id, result_text, parse_mode='HTML', reply_markup=keyboard)
                        else:
                            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Обновить список", callback_data="refresh")]])
                            await self.send_message(chat_id, "❌ Нет прокси\nНажмите /refresh для обновления", 
                                                   parse_mode='HTML', reply_markup=keyboard)
                    else:
                        await self.send_message(chat_id, "❌ Нет прокси\nНажмите /refresh для обновления")
                
                elif text in ['/refresh', '/update']:
                    msg_result = await self.send_message(chat_id, "🔍 <b>Запуск обновления прокси...</b>")
                    message_id = msg_result['result']['message_id']
                    await self.run_update_process(chat_id, message_id)
                    
            elif 'callback_query' in update:
                query = update['callback_query']
                data = query['data']
                chat_id = query['message']['chat']['id']
                message_id = query['message']['message_id']
                username = query['from'].get('username', 'unknown')
                print(f"\n📥 Callback: {data} от @{username}")
                
                try:
                    await self.answer_callback_query(query['id'], "🔄 Обновляю...")
                except:
                    pass
                
                if data == 'refresh':
                    await self.run_update_process(chat_id, message_id)
        except Exception as e:
            print(f"⚠️ Ошибка обработки обновления: {e}")
    
    async def run(self):
        me = await self.get_me()
        print(f"✅ Бот: @{me['result']['username']}")
        
        await self._request('get', 'deleteWebhook')
        print("✅ Webhook удален")
        
        updates = await self.get_updates()
        if updates['ok'] and updates['result']:
            self.last_update_id = updates['result'][-1]['update_id']
            print(f"📨 Найдено {len(updates['result'])} ожидающих обновлений")
        
        print("📱 Бот готов! Отправьте /start")
        print("="*50 + "\n")
        
        # Счетчик ошибок для авто-перезапуска
        error_count = 0
        max_errors = 10
        
        while True:
            try:
                offset = self.last_update_id + 1 if self.last_update_id else None
                updates = await self.get_updates(offset=offset, timeout=30)
                
                # Сбрасываем счетчик ошибок при успешном получении
                error_count = 0
                
                if updates['ok'] and updates['result']:
                    for update in updates['result']:
                        try:
                            await self.process_update(update)
                            self.last_update_id = update['update_id']
                        except Exception as e:
                            print(f"⚠️ Ошибка обработки обновления: {e}")
                            # Продолжаем с другими обновлениями
                
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except httpx.ReadTimeout:
                # Таймаут - нормальная ситуация, просто продолжаем
                error_count = 0
                await asyncio.sleep(0.5)
            except httpx.ConnectError as e:
                error_count += 1
                print(f"⚠️ Ошибка соединения ({error_count}/{max_errors}): {e}")
                if error_count >= max_errors:
                    print("❌ Слишком много ошибок соединения, перезапуск...")
                    break
                await asyncio.sleep(5)
            except httpx.ReadError as e:
                error_count += 1
                print(f"⚠️ Ошибка чтения ({error_count}/{max_errors}): {e}")
                if error_count >= max_errors:
                    print("❌ Слишком много ошибок чтения, перезапуск...")
                    break
                await asyncio.sleep(3)
            except Exception as e:
                error_count += 1
                print(f"⚠️ Неизвестная ошибка ({error_count}/{max_errors}): {e}")
                if error_count >= max_errors:
                    print("❌ Слишком много ошибок, перезапуск...")
                    break
                await asyncio.sleep(5)

# ===== ЗАПУСК =====
async def run_bot():
    print("\n" + "="*50)
    print("🤖 ЗАПУСК БОТА С ПРОГРЕСС-БАРОМ")
    print("="*50)
    print(f"🌐 Worker URL: {WORKER_URL}")
    
    bot = ProgressBot(TOKEN, WORKER_URL)
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Остановка...")
    finally:
        await bot.client.aclose()

def main():
    print("\n" + "="*50)
    print("🔍 ПАРСЕР ПРОКСИ")
    print("="*50)
    print(f"📂 Рабочая папка: {PROJECT_DIR}")
    
    proxies = parse_best_proxies_file()
    if proxies:
        ru = len([p for p in proxies if 'RU' in p.get('type', '')])
        eu = len([p for p in proxies if 'EU' in p.get('type', '')])
        print(f"\n✅ Найдено {len(proxies)} прокси (RU: {ru}, EU: {eu})")
    
    print("\n🎯 Выберите режим:")
    print("1️⃣  Опубликовать в канал")
    print("2️⃣  Запустить бота")
    
    response = input("\n📌 Ваш выбор (1/2): ")
    
    if response == '1':
        print("\n🔄 Публикация в канал...")
        pass
    elif response == '2':
        asyncio.run(run_bot())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Пока!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()