#!/usr/bin/env python3
import asyncio
import httpx
import json

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

async def delete_webhook():
    async with httpx.AsyncClient() as client:
        # Удаляем webhook
        url = f"{WORKER_URL}/bot{TOKEN}/deleteWebhook"
        print(f"📡 Запрос: {url}")
        response = await client.get(url)
        print("Результат удаления webhook:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        # Проверяем
        check_url = f"{WORKER_URL}/bot{TOKEN}/getWebhookInfo"
        check_response = await client.get(check_url)
        print("\n📊 Информация о webhook после удаления:")
        print(json.dumps(check_response.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(delete_webhook())