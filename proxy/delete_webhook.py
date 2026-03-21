#!/usr/bin/env python3
import asyncio
import httpx

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

async def delete_webhook():
    async with httpx.AsyncClient() as client:
        url = f"{WORKER_URL}/bot{TOKEN}/deleteWebhook"
        response = await client.get(url)
        print(f"Ответ: {response.json()}")

asyncio.run(delete_webhook())