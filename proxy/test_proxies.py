#!/usr/bin/env python3
import subprocess
import re
import os
import glob
from datetime import datetime
import time
import socket
import statistics
import json
import urllib.request
import ssl
import urllib.parse

# ===== ОПТИМИЗИРОВАННЫЕ НАСТРОЙКИ =====
PING_TIMEOUT = 10
PING_COUNT = 2
PING_INTERVAL = 1
MAX_PING = 800
MIN_PROXIES = 3
CHECK_LIMIT = 50
ACCEPT_PACKET_LOSS = True
SHOW_PROGRESS = True
# ================================

# ===== ПАРАМЕТРЫ СТАБИЛЬНОСТИ =====
STABILITY_TEST_ENABLED = True
STABILITY_SAMPLES = 2
STABILITY_INTERVAL = 0.3
MAX_JITTER = 250
MAX_PACKET_LOSS = 30
USE_TCP_PING = True
# ==================================

# ===== ТОКЕН ДЛЯ TELEGRAM =====
TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"


def clean_server(server):
    """Очищает имя сервера от недопустимых символов"""
    if not server:
        return server
    server = server.rstrip('.')
    server = server.strip()
    server = re.sub(r'^https?://', '', server)
    return server

def clean_proxy_link_full(link):
    """Полная очистка прокси-ссылки: сервер и secret"""
    if not link.startswith('tg://proxy?'):
        return link
    
    server_match = re.search(r'server=([^&]+)', link)
    if server_match:
        server_raw = server_match.group(1)
        server_clean = clean_server(server_raw)
        if server_clean != server_raw:
            link = link.replace(f'server={server_raw}', f'server={server_clean}')
    
    secret_match = re.search(r'secret=([^&]+)', link)
    if secret_match:
        secret_raw = secret_match.group(1)
        try:
            secret_decoded = urllib.parse.unquote(secret_raw)
            if secret_decoded != secret_raw:
                link = link.replace(f'secret={secret_raw}', f'secret={secret_decoded}')
        except:
            pass
    
    return link

# ===== ФУНКЦИИ УПРАВЛЕНИЯ VPN =====
def is_vpn_connected():
    try:
        result = subprocess.run(
            ['scutil', '--nc', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "Connected" in result.stdout and "EVA VPN" in result.stdout
    except:
        return False

def disconnect_vpn():
    print("🔌 Отключаю EVA VPN...")
    try:
        subprocess.run(
            ['scutil', '--nc', 'stop', 'EVA VPN'],
            capture_output=True,
            text=True,
            timeout=10
        )
        time.sleep(2)
        if not is_vpn_connected():
            print("✅ EVA VPN отключен")
            return True
        else:
            print("⚠️ Не удалось отключить VPN")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка отключения VPN: {e}")
        return False

def connect_vpn():
    print("🔌 Подключаю EVA VPN...")
    try:
        subprocess.run(
            ['scutil', '--nc', 'stop', 'EVA VPN'],
            capture_output=True,
            text=True,
            timeout=5
        )
        time.sleep(1)
        subprocess.run(
            ['scutil', '--nc', 'start', 'EVA VPN'],
            capture_output=True,
            text=True,
            timeout=15
        )
        for i in range(5):
            time.sleep(1)
            if is_vpn_connected():
                print(f"   VPN подключен через {i+1} сек")
                return True
        return False
    except Exception as e:
        print(f"⚠️ Ошибка подключения VPN: {e}")
        return False

def get_vpn_status():
    try:
        result = subprocess.run(
            ['scutil', '--nc', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'EVA VPN' in line:
                return "✅ Подключен" if 'Connected' in line else "❌ Отключен"
        return "❌ Не найден"
    except:
        return "❌ Ошибка"

class VPNContext:
    def __init__(self, debug=False):
        self.debug = debug
        self.was_connected = False
    
    def __enter__(self):
        self.was_connected = is_vpn_connected()
        if self.debug:
            print(f"📊 VPN до: {get_vpn_status()}")
        if self.was_connected:
            print("🌐 Временно отключаю VPN...")
            disconnect_vpn()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.was_connected:
            print("🌐 Восстанавливаю VPN...")
            connect_vpn()
        if self.debug:
            time.sleep(1)
            print(f"📊 VPN после: {get_vpn_status()}")

# ===== ФУНКЦИИ ПРОВЕРКИ СТАБИЛЬНОСТИ =====
def test_telegram_ping(server, port, timeout=5):
    test_url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    
    try:
        proxy_handler = urllib.request.ProxyHandler({
            'http': f'http://{server}:{port}',
            'https': f'http://{server}:{port}'
        })
        opener = urllib.request.build_opener(proxy_handler)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        start_time = time.time()
        req = urllib.request.Request(test_url, method='GET')
        
        with opener.open(req, timeout=timeout, context=ctx) as response:
            elapsed = (time.time() - start_time) * 1000
            data = response.read()
            
            if b'"ok":true' in data:
                return elapsed
            return None
            
    except Exception as e:
        return None

def test_proxy_stability(server, port, level='quick'):
    if level == 'quick':
        samples = 2
        max_ping = 400
        max_jitter = 200
        max_loss = 30
    else:
        samples = 5
        max_ping = 250
        max_jitter = 80
        max_loss = 10
    
    pings = []
    losses = 0
    
    for i in range(samples):
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
        if i < samples - 1:
            time.sleep(0.3)
    
    if not pings:
        return None, None, 100, False, None
    
    avg_ping = sum(pings) / len(pings)
    loss_percent = (losses / samples) * 100
    
    if len(pings) > 1:
        variance = sum((p - avg_ping) ** 2 for p in pings) / len(pings)
        jitter = variance ** 0.5
    else:
        jitter = 0
    
    telegram_ping = test_telegram_ping(server, port, timeout=5)
    
    if level == 'strict':
        if telegram_ping:
            avg_ping = telegram_ping
            print(f"   📡 Реальный Telegram ping: {avg_ping:.0f}мс")
        else:
            print(f"   ❌ Telegram не отвечает через прокси")
            return None, None, 100, False, None
    
    meets_criteria = (avg_ping <= max_ping and jitter <= max_jitter and loss_percent <= max_loss)
    
    return avg_ping, jitter, loss_percent, meets_criteria, None

def get_latest_proxy_files():
    ru_files = glob.glob("verified/*ru*.txt")
    eu_files = glob.glob("verified/*eu*.txt")
    all_files = glob.glob("verified/*all*.txt")
    
    latest_ru = max(ru_files, key=os.path.getctime) if ru_files else None
    latest_eu = max(eu_files, key=os.path.getctime) if eu_files else None
    latest_all = max(all_files, key=os.path.getctime) if all_files else None
    
    return latest_ru, latest_eu, latest_all

def test_port_availability(server, port=443, timeout=3):
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server, port))
        sock.close()
        
        if result == 0:
            response_time = (time.time() - start_time) * 1000
            return True, response_time
        return False, None
    except:
        return False, None

def test_stability(server, port=443, samples=2):
    times = []
    successes = 0
    
    for i in range(samples):
        available, response_time = test_port_availability(server, port, timeout=3)
        
        if available:
            successes += 1
            times.append(response_time)
        
        if i < samples - 1:
            time.sleep(0.3)
    
    if successes == 0:
        return None, None, 100, []
    
    avg_time = sum(times) / len(times)
    
    if len(times) > 1:
        jitter = statistics.stdev(times)
    else:
        jitter = 0
    
    packet_loss = ((samples - successes) / samples) * 100
    
    return avg_time, jitter, packet_loss, times

def calculate_quality_score(avg_time, jitter, packet_loss):
    if avg_time is None:
        return 0
    
    if avg_time < 100:
        time_score = 40
    elif avg_time < 200:
        time_score = 35
    elif avg_time < 300:
        time_score = 30
    elif avg_time < 400:
        time_score = 25
    else:
        time_score = 20
    
    if jitter < 30:
        jitter_score = 35
    elif jitter < 60:
        jitter_score = 30
    elif jitter < 100:
        jitter_score = 25
    else:
        jitter_score = 20
    
    if packet_loss < 5:
        loss_score = 25
    elif packet_loss < 10:
        loss_score = 20
    elif packet_loss < 15:
        loss_score = 15
    else:
        loss_score = 10
    
    return time_score + jitter_score + loss_score

def validate_proxy_link(link):
    try:
        if not link.startswith('tg://proxy?'):
            return False
        has_server = 'server=' in link
        has_port = 'port=' in link
        has_secret = 'secret=' in link
        return has_server and has_port and has_secret
    except:
        return False

def clean_proxy_link(link):
    link = re.sub(r'\.{2,}', '.', link)
    link = link.strip()
    return link

def extract_proxies_from_file(file_path, proxy_type):
    proxies = []
    
    if not file_path or not os.path.exists(file_path):
        return proxies
    
    if 'ru' in file_path.lower():
        real_type = '🇷🇺 RU'
    elif 'eu' in file_path.lower():
        real_type = '🇪🇺 EU'
    else:
        real_type = '🌍 ALL'
    
    print(f"\n📊 Проверка {real_type}: {os.path.basename(file_path)}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    lines = []
    if 'tg://proxy' in content:
        lines = [line.strip() for line in content.split('\n') if 'tg://proxy' in line]
    
    total = len(lines)
    checked = min(total, CHECK_LIMIT)
    print(f"   Всего: {total}, проверяем: {checked}")
    
    start_time = time.time()
    validated = 0
    unstable = 0
    failed = 0
    
    for i, line in enumerate(lines[:CHECK_LIMIT], 1):
        proxy_info = {}
        
        clean_link = clean_proxy_link(line)
        if not validate_proxy_link(clean_link):
            continue
        
        clean_link = clean_proxy_link_full(clean_link)
        
        proxy_info['link'] = clean_link
        proxy_info['type'] = real_type
        
        server_match = re.search(r'server=([^&]+)', clean_link)
        if not server_match:
            continue
        proxy_info['server'] = server_match.group(1)
        
        port_match = re.search(r'port=(\d+)', clean_link)
        proxy_info['port'] = int(port_match.group(1)) if port_match else 443
        
        if SHOW_PROGRESS:
            print(f"   [{i}/{checked}] {proxy_info['server']}:{proxy_info['port']}")
        
        avg_time, jitter, packet_loss, times = test_stability(
            proxy_info['server'], proxy_info['port'], STABILITY_SAMPLES
        )
        
        if avg_time is None:
            if SHOW_PROGRESS:
                print(f"      ❌ Порт недоступен")
            failed += 1
            continue
        
        if avg_time > MAX_PING:
            if SHOW_PROGRESS:
                print(f"      ⚠️ Время {avg_time:.0f}мс > {MAX_PING}мс")
            continue
            
        if jitter > MAX_JITTER:
            if SHOW_PROGRESS:
                print(f"      ⚠️ Джиттер {jitter:.0f}мс > {MAX_JITTER}мс")
            unstable += 1
            continue
            
        if packet_loss > MAX_PACKET_LOSS:
            if SHOW_PROGRESS:
                print(f"      ⚠️ Потери {packet_loss:.0f}% > {MAX_PACKET_LOSS}%")
            unstable += 1
            continue
        
        proxy_info['ping'] = avg_time
        proxy_info['jitter'] = jitter
        proxy_info['packet_loss'] = packet_loss
        proxy_info['quality_score'] = calculate_quality_score(avg_time, jitter, packet_loss)
        
        if SHOW_PROGRESS:
            quality_emoji = "🏆" if proxy_info['quality_score'] > 80 else "⭐️" if proxy_info['quality_score'] > 60 else "✅"
            print(f"      ✅ {quality_emoji} {avg_time:.0f}мс (±{jitter:.0f}мс) потери:{packet_loss:.0f}%")
        
        proxies.append(proxy_info)
        validated += 1
        
        if SHOW_PROGRESS and i % 10 == 0:
            elapsed = time.time() - start_time
            print(f"      Прогресс: {i}/{checked} ({elapsed:.0f}с), найдено: {validated}")
    
    elapsed = time.time() - start_time
    print(f"\n   📊 ИТОГ: ✅ {validated} стабильных, ⚠️ {unstable} нестабильных, ❌ {failed} недоступных")
    print(f"   ⏱️  Время: {elapsed:.0f}с")
    return proxies

def advanced_final_check(proxies, progress_callback=None):
    print("\n" + "="*70)
    print("🔬 ПРОВЕРКА СТАБИЛЬНОСТИ")
    print("="*70)
    
    if not proxies:
        print("❌ Нет прокси для проверки")
        return []
    
    quick_pass = []
    ru_quick_count = 0
    
    for i, p in enumerate(proxies[:30], 1):
        if 'link' not in p:
            continue
        
        is_ru = 'RU' in p.get('type', '') or p.get('country') == 'RU'
        
        port_match = re.search(r'port=(\d+)', p['link'])
        port = int(port_match.group(1)) if port_match else 443
        avg_ping, jitter, loss, passed, _ = test_proxy_stability(p['server'], port, level='quick')
        
        if passed:
            quick_pass.append(p)
            if is_ru:
                ru_quick_count += 1
                print(f"   ✅ RU прокси прошел быстрый отбор: {p['server']}")
    
    print(f"\n✅ Быстрый отбор: {len(quick_pass)} прокси (RU: {ru_quick_count})")
    
    if len(quick_pass) < 3:
        return quick_pass[:5]
    
    strict_pass = []
    ru_strict_count = 0
    
    for i, p in enumerate(quick_pass[:15], 1):
        is_ru = 'RU' in p.get('type', '') or p.get('country') == 'RU'
        
        port_match = re.search(r'port=(\d+)', p['link'])
        port = int(port_match.group(1)) if port_match else 443
        avg_ping, jitter, loss, passed, download_speed = test_proxy_stability(p['server'], port, level='strict')
        
        if passed:
            quality_score = ((300 - min(avg_ping, 300)) * 0.4 + (100 - min(jitter, 100)) * 0.35 + (100 - loss) * 0.25)
            p['quality_score'] = quality_score
            p['strict_stats'] = {'ping': avg_ping, 'jitter': jitter, 'loss': loss}
            if download_speed:
                p['download_speed'] = download_speed
            strict_pass.append(p)
            
            if is_ru:
                ru_strict_count += 1
                print(f"   ✅ RU прокси прошел жесткий отбор: {p['server']} (пинг={avg_ping:.0f}мс)")
    
    print(f"\n✅ Жесткий отбор: {len(strict_pass)} прокси (RU: {ru_strict_count})")
    
    ru_proxies = [p for p in strict_pass if 'RU' in p.get('type', '') or p.get('country') == 'RU']
    eu_proxies = [p for p in strict_pass if 'EU' in p.get('type', '') or p.get('country') not in ['RU', None]]
    
    ru_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    eu_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    
    print(f"\n📊 RU прокси: {len(ru_proxies)}, EU прокси: {len(eu_proxies)}")
    
    final_proxies = []
    for i in range(min(len(ru_proxies), 5)):
        final_proxies.append(ru_proxies[i])
    for i in range(min(len(eu_proxies), 10 - len(final_proxies))):
        final_proxies.append(eu_proxies[i])
    
    print(f"\n🏆 ИТОГО: {len(final_proxies)} прокси (RU: {min(len(ru_proxies), 5)})")
    return final_proxies[:10]

def save_proxies_to_file(proxies, filename="best_proxies.txt"):
    seen_servers = set()
    unique_proxies = []
    
    for p in proxies:
        if p['server'] not in seen_servers:
            seen_servers.add(p['server'])
            if 'link' in p:
                p['link'] = clean_proxy_link_full(p['link'])
            unique_proxies.append(p)
    
    unique_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    
    ru_proxies = [p for p in unique_proxies if 'RU' in p['type']]
    eu_proxies = [p for p in unique_proxies if 'EU' in p['type']]
    
    print(f"\n📊 После сортировки: 🇷🇺 RU: {len(ru_proxies)}, 🇪🇺 EU: {len(eu_proxies)}")
    
    ru_top = ru_proxies[:5]
    eu_top = eu_proxies[:5]
    
    final_proxies = []
    for i in range(max(len(ru_top), len(eu_top))):
        if i < len(ru_top):
            final_proxies.append(ru_top[i])
        if i < len(eu_top):
            final_proxies.append(eu_top[i])
    
    final_proxies = final_proxies[:10]
    
    with open(filename, 'w') as f:
        f.write(f"# Лучшие прокси от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Всего найдено: {len(unique_proxies)} (RU: {len(ru_proxies)}, EU: {len(eu_proxies)})\n")
        f.write(f"# В выдаче: {len(final_proxies)} прокси\n\n")
        
        for i, p in enumerate(final_proxies, 1):
            if p['quality_score'] > 80:
                quality = "🏆"
            elif p['quality_score'] > 60:
                quality = "⭐️"
            else:
                quality = "✅"
            
            stats = f"п:{p['ping']:.0f}мс дж:{p['jitter']:.0f}мс пот:{p['packet_loss']:.0f}%"
            mask = p.get('mask', '')
            if mask:
                f.write(f"# {i}. {p['type']} {quality} {p['server']} — {stats} | {mask}\n")
            else:
                f.write(f"# {i}. {p['type']} {quality} {p['server']} — {stats}\n")
            f.write(f"{p['link']}\n\n")
    
    with open('best_proxies.json', 'w', encoding='utf-8') as f:
        json.dump(final_proxies, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено в best_proxies.json")
    
    return final_proxies