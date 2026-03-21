#!/usr/bin/env python3
"""
Тестовый бот для проверки получения команд через Worker
"""

import asyncio
import httpx
import json
from datetime import datetime

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

class SimpleTestBot:
    def __init__(self, token, worker_url):
        self.token = token
        self.worker_url = worker_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        self.last_update_id = 0
    
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
    
    async def send_message(self, chat_id, text):
        return await self._request('post', 'sendMessage', json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        })
    
    async def run(self):
        # Проверяем бота
        me = await self.get_me()
        print(f"✅ Бот: @{me['result']['username']}")
        
        # Удаляем webhook
        await self._request('get', 'deleteWebhook')
        print("✅ Webhook удален")
        
        # Ждем немного
        await asyncio.sleep(1)
        
        # Получаем последние обновления
        updates = await self.get_updates()
        if updates['ok'] and updates['result']:
            self.last_update_id = updates['result'][-1]['update_id']
            print(f"📨 Найдено {len(updates['result'])} ожидающих обновлений:")
            for update in updates['result']:
                if 'message' in update:
                    msg = update['message']
                    text = msg.get('text', '')
                    username = msg['from'].get('username', 'unknown')
                    print(f"   - {text} от @{username}")
        else:
            print("📨 Нет ожидающих обновлений")
        
        print("\n📱 Бот готов! Отправьте /start в Telegram")
        print("="*50 + "\n")
        
        # Основной цикл polling
        error_count = 0
        while True:
            try:
                offset = self.last_update_id + 1 if self.last_update_id else None
                updates = await self.get_updates(offset=offset, timeout=30)
                
                # Сбрасываем счетчик ошибок при успехе
                error_count = 0
                
                if updates['ok'] and updates['result']:
                    for update in updates['result']:
                        await self.process_update(update)
                        self.last_update_id = update['update_id']
                
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                
                # Игнорируем некоторые ошибки
                if "Conflict" in error_msg:
                    print(f"⚠️ Конфликт polling (попытка {error_count}): возможно бот уже запущен")
                    if error_count > 3:
                        print("❌ Слишком много конфликтов, остановка...")
                        break
                    await asyncio.sleep(10)
                elif "ReadTimeout" in error_msg or "timeout" in error_msg.lower():
                    # Таймаут - нормальная ситуация, просто продолжаем
                    pass
                else:
                    print(f"⚠️ Ошибка ({error_count}): {e}")
                    if error_count > 10:
                        print("❌ Слишком много ошибок, остановка...")
                        break
                    await asyncio.sleep(5)
    
    async def process_update(self, update):
        """Обрабатывает обновление"""
        if 'message' in update:
            msg = update['message']
            text = msg.get('text', '')
            chat_id = msg['chat']['id']
            username = msg['from'].get('username', 'unknown')
            
            print(f"\n📥 ПОЛУЧЕНО СООБЩЕНИЕ: {text} от @{username}")
            
            if text == '/start':
                await self.send_message(chat_id, 
                    "✅ <b>Бот работает через Cloudflare Worker!</b>\n\n"
                    "Отправьте /refresh для обновления прокси",
                    parse_mode='HTML')
                print(f"   ✅ Отправлен ответ на /start")
            
            elif text == '/refresh':
                await self.send_message(chat_id, 
                    "🔄 <b>Обновление прокси начато!</b>",
                    parse_mode='HTML')
                print(f"   ✅ Отправлен ответ на /refresh")
            
            elif text == '/status':
                await self.send_message(chat_id, 
                    f"📊 <b>Статус бота</b>\n\n"
                    f"Last update ID: {self.last_update_id}\n"
                    f"Worker: {self.worker_url}",
                    parse_mode='HTML')
                print(f"   ✅ Отправлен ответ на /status")
            
            else:
                await self.send_message(chat_id, 
                    f"❓ Неизвестная команда: {text}\n\n"
                    "Доступные команды:\n"
                    "/start - показать приветствие\n"
                    "/refresh - обновить прокси\n"
                    "/status - показать статус",
                    parse_mode='HTML')
                print(f"   ✅ Отправлен ответ на неизвестную команду")
        
        elif 'callback_query' in update:
            query = update['callback_query']
            data = query['data']
            chat_id = query['message']['chat']['id']
            username = query['from'].get('username', 'unknown')
            
            print(f"\n📥 ПОЛУЧЕН CALLBACK: {data} от @{username}")
            
            # Отвечаем на callback
            await self._request('post', 'answerCallbackQuery', json={
                'callback_query_id': query['id'],
                'text': '✅ Получено!'
            })
            
            if data == 'refresh':
                await self.send_message(chat_id, "🔄 Обновление начато!")
                print(f"   ✅ Обновление запущено")

async def main():
    print("="*50)
    print("🤖 ТЕСТОВЫЙ БОТ (ПОЛЛИНГ ЧЕРЕЗ WORKER)")
    print("="*50)
    print(f"🌐 Worker URL: {WORKER_URL}")
    print("💡 Бот будет ждать команды /start, /refresh, /status")
    print("="*50 + "\n")
    
    bot = SimpleTestBot(TOKEN, WORKER_URL)
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Остановка...")
    finally:
        await bot.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())