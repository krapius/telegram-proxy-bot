#!/usr/bin/env python3
import asyncio
import httpx
import json
from telegram import Bot

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

class WorkerBot:
    def __init__(self, token, worker_url):
        self.token = token
        self.worker_url = worker_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        self.bot = Bot(token)
        self.last_update_id = 0
    
    async def _request(self, method, endpoint, **kwargs):
        """Отправляет запрос через Worker"""
        url = f"{self.worker_url}/bot{self.token}/{endpoint}"
        print(f"📡 {method.upper()} {endpoint}")
        
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
        
        # Получаем последние обновления
        updates = await self.get_updates()
        if updates['ok'] and updates['result']:
            self.last_update_id = updates['result'][-1]['update_id']
            print(f"📨 Найдено {len(updates['result'])} ожидающих обновлений")
        
        print("📱 Бот готов! Отправьте /start")
        print("="*50)
        
        # Основной цикл polling
        while True:
            try:
                # Получаем новые обновления
                offset = self.last_update_id + 1 if self.last_update_id else None
                updates = await self.get_updates(offset=offset, timeout=30)
                
                if updates['ok'] and updates['result']:
                    for update in updates['result']:
                        await self.process_update(update)
                        self.last_update_id = update['update_id']
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Ошибка: {e}")
                await asyncio.sleep(5)
    
    async def process_update(self, update):
        """Обрабатывает одно обновление"""
        if 'message' in update:
            msg = update['message']
            text = msg.get('text', '')
            chat_id = msg['chat']['id']
            username = msg['from'].get('username', 'unknown')
            
            print(f"\n📥 ПОЛУЧЕНО: {text} от @{username}")
            
            if text == '/start':
                await self.send_message(chat_id, "✅ <b>Бот работает через Worker!</b>\n\nОтправьте /refresh")
            elif text == '/refresh':
                await self.send_message(chat_id, "🔄 <b>Обновление прокси начато!</b>")

async def main():
    print("="*60)
    print("🤖 БОТ С РУЧНЫМ POLLING")
    print("="*60)
    print(f"🌐 Worker: {WORKER_URL}")
    
    bot = WorkerBot(TOKEN, WORKER_URL)
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Остановка...")
    finally:
        await bot.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())