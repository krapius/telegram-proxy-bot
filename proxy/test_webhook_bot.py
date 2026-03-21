#!/usr/bin/env python3
"""
Тестовый бот для проверки получения команд через новый Worker (webhook)
"""

import asyncio
import httpx
import json
from aiohttp import web
import socket

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-bp.krichencat.workers.dev"
LOCAL_HOST = "localhost"
LOCAL_PORT = 8080

class WebhookTestBot:
    def __init__(self, token, worker_url):
        self.token = token
        self.worker_url = worker_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        self.last_update_id = 0
        self.webhook_server = None
    
    async def _request(self, method, endpoint, **kwargs):
        url = f"{self.worker_url}/bot{self.token}/{endpoint}"
        try:
            if method == 'get':
                response = await self.client.get(url, params=kwargs.get('params'))
            else:
                response = await self.client.post(url, json=kwargs.get('json'))
            
            # Проверяем статус и содержимое
            print(f"   📡 {endpoint}: статус {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ⚠️ Ошибка HTTP {response.status_code}: {response.text[:200]}")
                return {'ok': False, 'error': f'HTTP {response.status_code}'}
            
            # Пробуем распарсить JSON
            try:
                return response.json()
            except Exception as e:
                print(f"   ⚠️ Ошибка парсинга JSON: {e}")
                print(f"   Ответ: {response.text[:200]}")
                return {'ok': False, 'error': str(e)}
                
        except Exception as e:
            print(f"⚠️ Ошибка запроса {endpoint}: {e}")
            return {'ok': False, 'error': str(e)}
    
    async def get_me(self):
        return await self._request('get', 'getMe')
    
    async def delete_webhook(self):
        return await self._request('get', 'deleteWebhook')
    
    async def set_webhook(self, url):
        return await self._request('get', 'setWebhook', params={'url': url})
    
    async def get_webhook_info(self):
        return await self._request('get', 'getWebhookInfo')
    
    async def send_message(self, chat_id, text):
        return await self._request('post', 'sendMessage', json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        })
    
    async def answer_callback_query(self, query_id, text=None):
        data = {'callback_query_id': query_id}
        if text:
            data['text'] = text
        return await self._request('post', 'answerCallbackQuery', json=data)
    
    async def process_update(self, update):
        """Обрабатывает обновление от Telegram"""
        print(f"\n📥 ПОЛУЧЕНО ОБНОВЛЕНИЕ:")
        print(json.dumps(update, indent=2, ensure_ascii=False)[:500])
        
        if 'message' in update:
            msg = update['message']
            text = msg.get('text', '')
            chat_id = msg['chat']['id']
            username = msg['from'].get('username', 'unknown')
            
            print(f"\n📥 СООБЩЕНИЕ: {text} от @{username}")
            
            if text == '/start':
                await self.send_message(chat_id, 
                    "✅ <b>Бот работает через новый Worker!</b>\n\n"
                    "Отправьте /refresh для обновления прокси\n"
                    "Отправьте /status для проверки статуса",
                    parse_mode='HTML')
                print(f"   ✅ Отправлен ответ на /start")
            
            elif text == '/refresh':
                await self.send_message(chat_id, 
                    "🔄 <b>Обновление прокси начато!</b>\n\n"
                    "Это может занять 1-2 минуты...",
                    parse_mode='HTML')
                print(f"   ✅ Отправлен ответ на /refresh")
            
            elif text == '/status':
                info = await self.get_webhook_info()
                await self.send_message(chat_id, 
                    f"📊 <b>Статус бота</b>\n\n"
                    f"Worker: {self.worker_url}\n"
                    f"Webhook: {info.get('result', {}).get('url', 'не установлен')}\n"
                    f"Ожидающих обновлений: {info.get('result', {}).get('pending_update_count', 0)}",
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
            
            print(f"\n📥 CALLBACK: {data} от @{username}")
            
            await self.answer_callback_query(query['id'], "✅ Получено!")
            
            if data == 'refresh':
                await self.send_message(chat_id, "🔄 Обновление начато!")
                print(f"   ✅ Обновление запущено")
    
    async def webhook_handler(self, request):
        """Обработчик webhook запросов"""
        try:
            update = await request.json()
            print(f"\n🌐 Получен webhook запрос")
            await self.process_update(update)
            return web.json_response({'ok': True})
        except Exception as e:
            print(f"⚠️ Ошибка обработки webhook: {e}")
            return web.json_response({'ok': False, 'error': str(e)})
    
    async def start_webhook_server(self):
        """Запускает локальный сервер для приема webhook"""
        app = web.Application()
        app.router.add_post('/webhook', self.webhook_handler)
        
        # Добавляем страницу статуса
        async def handle_status(request):
            info = await self.get_webhook_info()
            return web.json_response({
                'status': 'running',
                'bot': 'migumBot',
                'worker': self.worker_url,
                'webhook': info.get('result', {})
            })
        
        app.router.add_get('/', handle_status)
        app.router.add_get('/status', handle_status)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', LOCAL_PORT)
        await site.start()
        
        print(f"🌐 Webhook сервер запущен на http://{LOCAL_HOST}:{LOCAL_PORT}")
        print(f"   POST /webhook - принимает обновления от Telegram")
        print(f"   GET /status - статус бота")
        
        return runner
    
    async def run(self):
        """Основной метод запуска бота"""
        print("="*60)
        print("🤖 ТЕСТОВЫЙ БОТ (WEBHOOK ЧЕРЕЗ НОВЫЙ WORKER)")
        print("="*60)
        print(f"🌐 Worker URL: {self.worker_url}")
        print(f"🌐 Локальный сервер: http://{LOCAL_HOST}:{LOCAL_PORT}/webhook")
        print("="*60 + "\n")
        
        # Проверяем подключение к Worker
        print("1️⃣ Проверка подключения к Worker...")
        me = await self.get_me()
        if not me.get('ok'):
            print(f"❌ Не удалось подключиться к Worker: {me}")
            return
        
        print(f"✅ Бот: @{me['result']['username']}")
        
        # Удаляем старый webhook
        print("\n2️⃣ Удаление старого webhook...")
        result = await self.delete_webhook()
        print(f"   Результат: {result}")
        
        # Устанавливаем новый webhook
        print("\n3️⃣ Установка нового webhook...")
        webhook_url = f"{self.worker_url}/webhook"
        result = await self.set_webhook(webhook_url)
        print(f"   Результат: {result}")
        
        if result.get('ok'):
            print(f"✅ Webhook установлен: {webhook_url}")
            
            # Проверяем статус webhook
            print("\n4️⃣ Проверка статуса webhook...")
            info = await self.get_webhook_info()
            if info.get('ok'):
                webhook_info = info.get('result', {})
                print(f"\n📊 Webhook информация:")
                print(f"   URL: {webhook_info.get('url')}")
                print(f"   Ожидающих обновлений: {webhook_info.get('pending_update_count', 0)}")
                if webhook_info.get('last_error_message'):
                    print(f"   ⚠️ Последняя ошибка: {webhook_info.get('last_error_message')}")
            
            # Запускаем локальный сервер
            print("\n5️⃣ Запуск локального сервера...")
            runner = await self.start_webhook_server()
            
            print("\n" + "="*60)
            print("📱 Бот готов к работе!")
            print("📌 Отправьте команду /start в Telegram @migumBot")
            print("💡 Бот работает через webhook (новый Worker)")
            print("="*60 + "\n")
            
            # Держим сервер запущенным
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                print("\n👋 Остановка...")
            finally:
                await runner.cleanup()
                await self.client.aclose()
                
        else:
            print(f"❌ Ошибка установки webhook: {result}")

async def main():
    bot = WebhookTestBot(TOKEN, WORKER_URL)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())