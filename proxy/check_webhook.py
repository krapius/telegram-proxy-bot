#!/usr/bin/env python3
import asyncio
import httpx
import json

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

async def check_webhook():
    async with httpx.AsyncClient() as client:
        # Проверяем информацию о webhook
        url = f"{WORKER_URL}/bot{TOKEN}/getWebhookInfo"
        response = await client.get(url)
        print("📊 Информация о webhook:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        # Проверяем, есть ли ожидающие обновления
        url = f"{WORKER_URL}/bot{TOKEN}/getUpdates"
        response = await client.get(url)
        print("\n📨 Ожидающие обновления:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

asyncio.run(check_webhook())