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
# ===== КОНЕЦ ФУНКЦИЙ VPN =====

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

def test_stability(server, port=443, samples=STABILITY_SAMPLES):
    times = []
    successes = 0
    
    for i in range(samples):
        available, response_time = test_port_availability(server, port, timeout=3)
        
        if available:
            successes += 1
            times.append(response_time)
        
        if i < samples - 1:
            time.sleep(STABILITY_INTERVAL)
    
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

def save_proxies_to_file(proxies, filename="best_proxies.txt"):
    seen_servers = set()
    unique_proxies = []
    
    for p in proxies:
        if p['server'] not in seen_servers:
            seen_servers.add(p['server'])
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
    
    # Сохраняем в TXT
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
    
    # Сохраняем также в JSON с полными данными
    with open('best_proxies.json', 'w', encoding='utf-8') as f:
        json.dump(final_proxies, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено в best_proxies.json")
    
    return final_proxies

def main():
    print("\n" + "="*70)
    print("🔍 ПОИСК ПРОКСИ (ОПТИМИЗИРОВАННЫЙ)")
    print("="*70)
    print(f"⏱️  Таймаут: {PING_TIMEOUT}с, проверяем: {CHECK_LIMIT} прокси")
    print(f"📈 Тест: {STABILITY_SAMPLES} TCP-соединений")
    print(f"📊 VPN статус: {get_vpn_status()}")
    
    ru_file, eu_file, all_file = get_latest_proxy_files()
    
    print(f"\n📂 Найдены файлы:")
    print(f"   🇷🇺 RU: {ru_file if ru_file else 'нет'}")
    print(f"   🇪🇺 EU: {eu_file if eu_file else 'нет'}")
    
    all_proxies = []
    
    with VPNContext():
        if ru_file:
            print(f"\n{'='*70}")
            ru_proxies = extract_proxies_from_file(ru_file, "🇷🇺 RU")
            all_proxies.extend(ru_proxies)
        
        if eu_file:
            print(f"\n{'='*70}")
            eu_proxies = extract_proxies_from_file(eu_file, "🇪🇺 EU")
            all_proxies.extend(eu_proxies)
    
    if not all_proxies:
        print("\n❌ Нет стабильных прокси")
        return
    
    final_proxies = save_proxies_to_file(all_proxies)
    
    print(f"\n{'='*70}")
    print(f"✅ РЕЗУЛЬТАТЫ")
    print(f"{'='*70}")
    print(f"📊 Всего стабильных: {len(all_proxies)}")
    
    ru_count = len([p for p in all_proxies if 'RU' in p['type']])
    eu_count = len([p for p in all_proxies if 'EU' in p['type']])
    print(f"   🇷🇺 RU: {ru_count}")
    print(f"   🇪🇺 EU: {eu_count}")
    
    print(f"\n📋 Отобрано для Telegram: {len(final_proxies)} прокси")
    print(f"\n📁 Файл сохранен: best_proxies.txt")
    print(f"\n📊 VPN статус после проверки: {get_vpn_status()}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Пока!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()