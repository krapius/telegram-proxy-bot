#!/usr/bin/env python3
import subprocess
import re
import os
import glob
from datetime import datetime
import time

# ===== ОСЛАБЛЕННЫЕ НАСТРОЙКИ =====
PING_TIMEOUT = 15          # Увеличили с 10 до 15 секунд
PING_COUNT = 2             # Уменьшили с 3 до 2 попыток
PING_INTERVAL = 1          # Интервал между пингами
MAX_PING = 800             # Увеличили с 500 до 800 мс
MIN_PROXIES = 3            # Уменьшили с 5 до 3
CHECK_LIMIT = 100          # Увеличили с 40 до 100 прокси
ACCEPT_PACKET_LOSS = True  # Принимать прокси с потерей пакетов
SHOW_PROGRESS = True       # Показывать прогресс проверки
# ================================

# ===== ФУНКЦИИ УПРАВЛЕНИЯ VPN =====
def is_vpn_connected():
    """Проверяет, подключен ли VPN"""
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
    """Отключает VPN по имени"""
    print("🔌 Отключаю EVA VPN...")
    try:
        subprocess.run(
            ['scutil', '--nc', 'stop', 'EVA VPN'],
            capture_output=True,
            text=True,
            timeout=10
        )
        time.sleep(3)
        
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
    """Подключает VPN по имени"""
    print("🔌 Подключаю EVA VPN...")
    try:
        subprocess.run(
            ['scutil', '--nc', 'start', 'EVA VPN'],
            capture_output=True,
            text=True,
            timeout=15
        )
        time.sleep(5)
        
        if is_vpn_connected():
            print("✅ EVA VPN подключен")
            return True
        else:
            print("⚠️ Не удалось подключить VPN")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка подключения VPN: {e}")
        return False

def get_vpn_status():
    """Возвращает статус VPN"""
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
    """Контекстный менеджер для временного отключения VPN"""
    def __init__(self, debug=False):
        self.debug = debug
        self.was_connected = False
    
    def __enter__(self):
        self.was_connected = is_vpn_connected()
        if self.debug:
            print(f"📊 VPN до: {get_vpn_status()}")
        
        if self.was_connected:
            print("🌐 Временно отключаю VPN для проверки пинга...")
            disconnect_vpn()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.was_connected:
            print("🌐 Восстанавливаю VPN...")
            connect_vpn()
        
        if self.debug:
            time.sleep(2)
            print(f"📊 VPN после: {get_vpn_status()}")
# ===== КОНЕЦ ФУНКЦИЙ VPN =====

def get_latest_proxy_files():
    """Находит самые свежие файлы с прокси"""
    ru_files = glob.glob("verified/*ru*.txt")
    eu_files = glob.glob("verified/*eu*.txt")
    all_files = glob.glob("verified/*all*.txt")
    
    latest_ru = max(ru_files, key=os.path.getctime) if ru_files else None
    latest_eu = max(eu_files, key=os.path.getctime) if eu_files else None
    latest_all = max(all_files, key=os.path.getctime) if all_files else None
    
    return latest_ru, latest_eu, latest_all

def test_ping_live(server):
    """Проверяет пинг с ослабленными требованиями"""
    try:
        if SHOW_PROGRESS:
            print(f"      ⏳ {server}...", end="", flush=True)
        else:
            print(f"      ⏳ {server}...", end="")
            
        result = subprocess.run(
            ['ping', '-c', str(PING_COUNT), '-W', str(PING_TIMEOUT), 
             '-i', str(PING_INTERVAL), server],
            capture_output=True,
            text=True,
            timeout=PING_TIMEOUT * PING_COUNT + 5
        )
        
        # Анализируем результат
        if result.returncode == 0:
            # Ищем средний пинг
            for line in result.stdout.split('\n'):
                if 'avg' in line:
                    parts = line.split('=')
                    if len(parts) > 1:
                        stats = parts[1].strip().split('/')
                        if len(stats) >= 2:
                            ping = float(stats[1])
                            if ping <= MAX_PING:
                                print(f" {ping:.1f}ms ✅")
                                return ping
                            else:
                                print(f" {ping:.1f}ms ⚠️ (высокий)")
                                return ping  # Всё равно принимаем
            
            # Если не нашли avg но сервер ответил
            print(" ✅ (ответ есть)")
            return 999  # Высокий пинг, но работает
            
        elif ACCEPT_PACKET_LOSS and "100% packet loss" not in result.stderr:
            # Есть потеря пакетов, но не 100%
            print(" ⚠️ (с потерями)")
            return 999
            
        else:
            print(" ❌")
            return None
            
    except subprocess.TimeoutExpired:
        print(" ❌ (таймаут)")
        return None
    except Exception as e:
        if SHOW_PROGRESS:
            print(f" ❌ (ошибка)")
        else:
            print(" ❌")
        return None

def extract_proxies_from_file(file_path, proxy_type):
    """Извлекает прокси с ослабленной фильтрацией"""
    proxies = []
    
    if not file_path or not os.path.exists(file_path):
        return proxies
    
    # Определяем регион из имени файла
    if 'ru' in file_path.lower():
        real_type = '🇷🇺 RU'
    elif 'eu' in file_path.lower():
        real_type = '🇪🇺 EU'
    else:
        real_type = '🌍 ALL'
    
    print(f"\n📊 Проверка {real_type}: {os.path.basename(file_path)}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Парсим прокси (разные форматы файлов)
    lines = []
    if 'tg://proxy' in content:
        # Простой список ссылок
        lines = [line.strip() for line in content.split('\n') if 'tg://proxy' in line]
    else:
        # Сложный формат с описаниями
        blocks = content.split('#')
        for block in blocks:
            if 'tg://proxy' in block:
                for line in block.split('\n'):
                    if 'tg://proxy' in line:
                        lines.append(line.strip())
    
    total = len(lines)
    checked = min(total, CHECK_LIMIT)
    print(f"   Всего: {total}, проверяем: {checked}")
    
    start_time = time.time()
    
    for i, line in enumerate(lines[:CHECK_LIMIT], 1):
        proxy_info = {}
        proxy_info['link'] = line
        proxy_info['type'] = real_type
        
        # Извлекаем сервер
        server_match = re.search(r'server=([^&]+)', line)
        if not server_match:
            continue
        proxy_info['server'] = server_match.group(1)
        
        # Извлекаем порт
        port_match = re.search(r'port=(\d+)', line)
        proxy_info['port'] = port_match.group(1) if port_match else '443'
        
        # Извлекаем секрет для маскировки
        secret_match = re.search(r'secret=([a-f0-9]+)', line)
        if secret_match:
            secret = secret_match.group(1)
            if secret.startswith('ee'):
                try:
                    hex_part = secret[2:]
                    if hex_part:
                        domain_bytes = bytes.fromhex(hex_part)
                        domain = domain_bytes.decode('utf-8', errors='ignore').strip('\x00')
                        domain = ''.join(c for c in domain if ord(c) >= 32 and ord(c) < 127)
                        if domain and len(domain) < 50 and '.' in domain:
                            proxy_info['mask'] = domain
                except:
                    pass
        
        # Показываем прогресс
        if SHOW_PROGRESS and i % 10 == 0:
            elapsed = time.time() - start_time
            print(f"      Прогресс: {i}/{checked} ({elapsed:.0f}с)")
        
        # Проверяем пинг
        ping = test_ping_live(proxy_info['server'])
        if ping:
            proxy_info['ping'] = ping
            proxies.append(proxy_info)
    
    elapsed = time.time() - start_time
    print(f"   ✅ Найдено: {len(proxies)} из {checked} за {elapsed:.0f}с")
    return proxies

def save_proxies_to_file(proxies, filename="best_proxies.txt"):
    """Сохраняет прокси в файл"""
    ru_count = len([p for p in proxies if 'RU' in p['type']])
    eu_count = len([p for p in proxies if 'EU' in p['type']])
    
    with open(filename, 'w') as f:
        f.write(f"# Лучшие прокси от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Всего: {len(proxies)} (RU: {ru_count}, EU: {eu_count})\n")
        f.write(f"# Настройки: таймаут={PING_TIMEOUT}с, макс.пинг={MAX_PING}мс, проверено={CHECK_LIMIT}\n\n")
        
        for i, p in enumerate(proxies[:20], 1):  # Топ-20
            # Определяем эмодзи скорости
            if p['ping'] < 50:
                speed = "⚡️"
            elif p['ping'] < 100:
                speed = "✅"
            elif p['ping'] < 150:
                speed = "⚠️"
            else:
                speed = "🐢"
            
            # Информация о прокси
            mask = p.get('mask', '')
            if mask:
                f.write(f"# {i}. {p['type']} {p['server']} — {speed} {p['ping']:.1f}ms | {mask}\n")
            else:
                f.write(f"# {i}. {p['type']} {p['server']} — {speed} {p['ping']:.1f}ms\n")
            
            f.write(f"{p['link']}\n\n")
    
    return ru_count, eu_count

def main():
    print("\n" + "="*70)
    print("🔍 ПОИСК ПРОКСИ (ОСЛАБЛЕННЫЕ НАСТРОЙКИ)")
    print("="*70)
    print(f"⏱️  Таймаут: {PING_TIMEOUT}с, попыток: {PING_COUNT}")
    print(f"📊 Макс. пинг: {MAX_PING}мс, проверяем: {CHECK_LIMIT} прокси")
    print(f"📶 Принимать с потерями: {ACCEPT_PACKET_LOSS}")
    print(f"📊 VPN статус: {get_vpn_status()}")
    
    # Получаем последние файлы
    ru_file, eu_file, all_file = get_latest_proxy_files()
    
    print(f"\n📂 Найдены файлы:")
    print(f"   🇷🇺 RU: {ru_file if ru_file else 'нет'}")
    print(f"   🇪🇺 EU: {eu_file if eu_file else 'нет'}")
    print(f"   🌍 ALL: {all_file if all_file else 'нет'}")
    
    all_proxies = []
    
    # Временно отключаем VPN для проверки пинга
    with VPNContext():
        # Сначала EU (их обычно больше)
        if eu_file:
            print(f"\n{'='*70}")
            eu_proxies = extract_proxies_from_file(eu_file, "🇪🇺 EU")
            all_proxies.extend(eu_proxies)
        
        # Потом RU
        if ru_file:
            print(f"\n{'='*70}")
            ru_proxies = extract_proxies_from_file(ru_file, "🇷🇺 RU")
            all_proxies.extend(ru_proxies)
    
    # Если мало прокси, берем из общего файла
    if len(all_proxies) < MIN_PROXIES and all_file:
        print(f"\n{'='*70}")
        print(f"⚠️  Мало прокси ({len(all_proxies)}), беру из общего файла")
        with VPNContext():
            all_proxies = extract_proxies_from_file(all_file, "🌍 ALL")
    
    if not all_proxies:
        print("\n❌ Нет рабочих прокси")
        return
    
    # Сортируем по пингу
    all_proxies.sort(key=lambda x: x.get('ping', 999))
    
    # Сохраняем в файл
    ru_count, eu_count = save_proxies_to_file(all_proxies)
    
    print(f"\n{'='*70}")
    print(f"✅ РЕЗУЛЬТАТЫ (ОСЛАБЛЕННЫЕ НАСТРОЙКИ)")
    print(f"{'='*70}")
    print(f"📊 Всего найдено: {len(all_proxies)} прокси")
    print(f"   🇷🇺 RU: {ru_count}")
    print(f"   🇪🇺 EU: {eu_count}")
    print(f"   🌍 Другие: {len(all_proxies) - ru_count - eu_count}")
    
    # Показываем топ-10
    print(f"\n📋 ТОП-10 БЫСТРЫХ ПРОКСИ:")
    print(f"{'='*70}")
    for i, p in enumerate(all_proxies[:10], 1):
        if p['ping'] < 50:
            marker = "⚡️"
        elif p['ping'] < 100:
            marker = "✅"
        elif p['ping'] < 150:
            marker = "⚠️"
        else:
            marker = "🐢"
        
        mask_info = f" | {p['mask']}" if 'mask' in p else ""
        print(f"{i}. {p['type']} {p['server']} — {marker} {p['ping']:.1f}ms{mask_info}")
    
    print(f"\n📁 Файл сохранен: best_proxies.txt")
    print(f"\n📊 VPN статус после проверки: {get_vpn_status()}")
    
    # Сравнение с жесткими настройками
    print(f"\n{'='*70}")
    print("📊 СРАВНЕНИЕ С ЖЕСТКИМИ НАСТРОЙКАМИ")
    print(f"{'='*70}")
    print(f"Параметр            | Жесткие  | Мягкие (текущие)")
    print(f"--------------------|----------|-----------------")
    print(f"Таймаут             | 10с      | {PING_TIMEOUT}с")
    print(f"Попыток пинга       | 3        | {PING_COUNT}")
    print(f"Макс. пинг          | 500мс    | {MAX_PING}мс")
    print(f"Проверяем прокси    | 40       | {CHECK_LIMIT}")
    print(f"Потери пакетов      | Нет      | {'Да' if ACCEPT_PACKET_LOSS else 'Нет'}")
    print(f"{'='*70}")
    print(f"✅ Найдено прокси    | 2-5      | {len(all_proxies)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Пока!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()