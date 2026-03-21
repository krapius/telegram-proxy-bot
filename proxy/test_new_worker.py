#!/usr/bin/env python3
"""
Тест бота с новым рабочим Worker
"""

import asyncio
import httpx
import json

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-bp.krichencat.workers.dev"  # Новый рабочий Worker

class TestBot:
    def __init__(self, token, worker_url):
        self.token = token
        self.worker_url = worker_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        self.last_update_id = 0
    
    async def _request(self, method, endpoint, **kwargs):
        url = f"{self.worker_url}/bot{self.token}/{endpoint}"
        try:
            if method == 'get':
                response = await self.client.get(url, params=kwargs.get('params'))
            else:
                response = await self.client.post(url, json=kwargs.get('json'))
            
            if response.status_code != 200:
                print(f"⚠️ HTTP {response.status_code}: {response.text[:100]}")
                return None
            
            return response.json()
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            return None
    
    async def get_me(self):
        return await self._request('get', 'getMe')
    
    async def delete_webhook(self):
        return await self._request('get', 'deleteWebhook')
    
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
        print("="*60)
        print("🤖 ТЕСТ БОТА (НОВЫЙ РАБОЧИЙ WORKER)")
        print("="*60)
        print(f"🌐 Worker URL: {self.worker_url}")
        print("="*60 + "\n")
        
        # Проверяем бота
        me = await self.get_me()
        if not me or not me.get('ok'):
            print(f"❌ Не удалось подключиться")
            return
        
        print(f"✅ Бот: @{me['result']['username']}")
        
        # Удаляем webhook
        result = await self.delete_webhook()
        print(f"✅ Webhook удален: {result}")
        
        # Получаем последние обновления
        updates = await self.get_updates()
        if updates and updates.get('ok') and updates.get('result'):
            self.last_update_id = updates['result'][-1]['update_id']
            print(f"📨 Найдено {len(updates['result'])} ожидающих обновлений")
            for update in updates['result']:
                if 'message' in update:
                    msg = update['message']
                    print(f"   - {msg.get('text')} от @{msg['from'].get('username')}")
        
        print("\n📱 Бот готов! Отправьте /start в Telegram")
        print("="*60 + "\n")
        
        # Основной цикл polling
        while True:
            try:
                offset = self.last_update_id + 1 if self.last_update_id else None
                updates = await self.get_updates(offset=offset, timeout=30)
                
                if updates and updates.get('ok') and updates.get('result'):
                    for update in updates['result']:
                        await self.process_update(update)
                        self.last_update_id = update['update_id']
                
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Ошибка: {e}")
                await asyncio.sleep(5)
    
    async def process_update(self, update):
        if 'message' in update:
            msg = update['message']
            text = msg.get('text', '')
            chat_id = msg['chat']['id']
            username = msg['from'].get('username', 'unknown')
            
            print(f"\n📥 ПОЛУЧЕНО: {text} от @{username}")
            
            if text == '/start':
                await self.send_message(chat_id, 
                    "✅ <b>Бот работает через новый Worker!</b>\n\n"
                    "Доступные команды:\n"
                    "/start - это сообщение\n"
                    "/refresh - обновить прокси\n"
                    "/status - статус бота")
                print(f"   ✅ Ответ отправлен")
            
            elif text == '/refresh':
                await self.send_message(chat_id, 
                    "🔄 <b>Обновление прокси начато!</b>\n\n"
                    "Это может занять 1-2 минуты...")
                print(f"   ✅ Обновление запущено")
            
            elif text == '/status':
                await self.send_message(chat_id, 
                    f"📊 <b>Статус бота</b>\n\n"
                    f"Worker: {self.worker_url}\n"
                    f"Last update ID: {self.last_update_id}")
                print(f"   ✅ Статус отправлен")

async def main():
    bot = TestBot(TOKEN, WORKER_URL)
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Остановка...")
    finally:
        await bot.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())