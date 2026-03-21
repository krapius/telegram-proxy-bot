#!/usr/bin/env python3
import asyncio
import httpx
import json

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

async def test_getupdates():
    async with httpx.AsyncClient() as client:
        # Запрос к Telegram API через Worker
        url = f"{WORKER_URL}/bot{TOKEN}/getUpdates"
        print(f"📡 Запрос: {url}")
        
        response = await client.get(url)
        print(f"Статус: {response.status_code}")
        
        data = response.json()
        print(f"Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Если есть сообщения, покажем их
        if data.get('ok') and data.get('result'):
            print(f"\n📨 Найдено {len(data['result'])} обновлений:")
            for update in data['result']:
                if 'message' in update:
                    msg = update['message']
                    print(f"   - {msg.get('text')} от @{msg['from']['username']}")

asyncio.run(test_getupdates())