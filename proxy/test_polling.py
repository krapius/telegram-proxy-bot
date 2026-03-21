#!/usr/bin/env python3
import asyncio
import httpx
import json

TOKEN = "8664454935:AAFPk1ehMIJB1r9MrDRTrb9JDtpHYjg1Vjc"
WORKER_URL = "https://tg-pr.krichencat.workers.dev"

async def test_polling():
    async with httpx.AsyncClient() as client:
        # Получаем последнее обновление
        url = f"{WORKER_URL}/bot{TOKEN}/getUpdates"
        
        # Сначала получаем последний update_id
        resp = await client.get(url)
        data = resp.json()
        
        if data.get('result'):
            last_update_id = data['result'][-1]['update_id']
            print(f"Последний update_id: {last_update_id}")
            
            # Пытаемся получить новые обновления с offset
            offset = last_update_id + 1
            print(f"Запрашиваю обновления с offset={offset}")
            
            resp2 = await client.get(url, params={"offset": offset, "timeout": 30})
            data2 = resp2.json()
            print(f"Результат: {json.dumps(data2, indent=2)}")
        else:
            print("Нет обновлений")

if __name__ == "__main__":
    asyncio.run(test_polling())