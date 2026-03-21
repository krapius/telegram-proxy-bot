#!/usr/bin/env python3
import asyncio
import httpx

WORKER_URL = "https://telegram-proxy-bot.krichencat.workers.dev"
TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"

async def poll():
    async with httpx.AsyncClient() as client:
        offset = 0
        print("🔄 Запуск polling...")
        while True:
            url = f"{WORKER_URL}/bot{TOKEN}/getUpdates"
            params = {"offset": offset + 1, "timeout": 30}
            try:
                resp = await client.get(url, params=params)
                data = resp.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        print(f"📥 Получено: {update.get('message', {}).get('text')}")
                        # Отправляем на обработку
                        await client.post(WORKER_URL, json=update)
                        offset = update['update_id']
            except Exception as e:
                print(f"Ошибка: {e}")
            await asyncio.sleep(1)

asyncio.run(poll())