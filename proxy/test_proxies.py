
#!/usr/bin/env python3
import re
import os
import glob
import time
import socket
import statistics
import json
from datetime import datetime

# ===== НАСТРОЙКИ =====
CHECK_LIMIT = 50
MAX_PING = 800
MAX_JITTER = 250
MAX_PACKET_LOSS = 30
STABILITY_SAMPLES = 2
SHOW_PROGRESS = True
# ====================

def clean_server(server):
    if not server:
        return server
    server = server.rstrip('.')
    server = server.strip()
    server = re.sub(r'^https?://', '', server)
    return server

def clean_proxy_link_full(link):
    if not link.startswith('tg://proxy?'):
        return link
    server_match = re.search(r'server=([^&]+)', link)
    if server_match:
        server_raw = server_match.group(1)
        server_clean = clean_server(server_raw)
        if server_clean != server_raw:
            link = link.replace(f'server={server_raw}', f'server={server_clean}')
    return link

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
            return True, (time.time() - start_time) * 1000
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
        return 'server=' in link and 'port=' in link and 'secret=' in link
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
    
    if proxy_type == 'ru':
        real_type = '🇷🇺 RU'
    elif proxy_type == 'eu':
        real_type = '🇪🇺 EU'
    else:
        real_type = '🌍 ALL'
    
    print(f"\n📊 Проверка {real_type}: {os.path.basename(file_path)}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    lines = [line.strip() for line in content.split('\n') if 'tg://proxy' in line]
    total = len(lines)
    checked = min(total, CHECK_LIMIT)
    print(f"   Всего: {total}, проверяем: {checked}")
    
    validated = 0
    for i, line in enumerate(lines[:CHECK_LIMIT], 1):
        clean_link = clean_proxy_link(line)
        if not validate_proxy_link(clean_link):
            continue
        clean_link = clean_proxy_link_full(clean_link)
        
        proxy_info = {'link': clean_link, 'type': real_type}
        server_match = re.search(r'server=([^&]+)', clean_link)
        if not server_match:
            continue
        proxy_info['server'] = server_match.group(1)
        port_match = re.search(r'port=(\d+)', clean_link)
        proxy_info['port'] = int(port_match.group(1)) if port_match else 443
        
        avg_time, jitter, packet_loss, _ = test_stability(proxy_info['server'], proxy_info['port'])
        
        if avg_time is None:
            continue
        if avg_time > MAX_PING:
            continue
        if jitter > MAX_JITTER:
            continue
        if packet_loss > MAX_PACKET_LOSS:
            continue
        
        proxy_info['ping'] = avg_time
        proxy_info['jitter'] = jitter
        proxy_info['packet_loss'] = packet_loss
        proxy_info['quality_score'] = calculate_quality_score(avg_time, jitter, packet_loss)
        proxies.append(proxy_info)
        validated += 1
        
        if SHOW_PROGRESS and i % 10 == 0:
            print(f"      Прогресс: {i}/{checked}, найдено: {validated}")
    
    print(f"\n   📊 ИТОГ: ✅ {validated} стабильных")
    return proxies

def save_proxies_to_file(proxies, filename="best_proxies.txt"):
    if not proxies:
        return []
    
    seen_servers = set()
    unique_proxies = []
    for p in proxies:
        if p['server'] not in seen_servers:
            seen_servers.add(p['server'])
            if 'link' in p:
                p['link'] = clean_proxy_link_full(p['link'])
            unique_proxies.append(p)
    
    unique_proxies.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
    
    ru_proxies = [p for p in unique_proxies if '🇷🇺' in p['type']]
    eu_proxies = [p for p in unique_proxies if '🇪🇺' in p['type']]
    
    print(f"\n📊 Результаты фильтрации: RU={len(ru_proxies)}, EU={len(eu_proxies)}")
    
    ru_top = ru_proxies[:5]
    eu_top = eu_proxies[:5]
    
    final_proxies = ru_top + eu_top
    final_proxies = final_proxies[:10]
    
    print(f"🏆 В финальный список попало: RU={len(ru_top)}, EU={len(eu_top)}")
    
    with open(filename, 'w') as f:
        f.write(f"# Лучшие прокси от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Всего стабильных: {len(unique_proxies)} (RU: {len(ru_proxies)}, EU: {len(eu_proxies)})\n")
        f.write(f"# В выдаче: {len(final_proxies)} прокси\n\n")
        for i, p in enumerate(final_proxies, 1):
            stats = f"п:{p['ping']:.0f}мс дж:{p['jitter']:.0f}мс пот:{p['packet_loss']:.0f}%"
            f.write(f"# {i}. {p['type']} {p['server']} — {stats}\n")
            f.write(f"{p['link']}\n\n")
    
    with open('best_proxies.json', 'w', encoding='utf-8') as f:
        json.dump(final_proxies, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено {len(final_proxies)} прокси в best_proxies.json")
    
    return final_proxies
EOF