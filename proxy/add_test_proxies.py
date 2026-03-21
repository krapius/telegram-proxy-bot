#!/usr/bin/env python3
import httpx

WORKER_URL = "https://telegram-proxy-bot.krichencat.workers.dev"

test_proxies = [
    {
        "link": "tg://proxy?server=37.139.42.151&port=443&secret=ee4f6d6b6b6b6b6b6b6b6b6b6b6b6b6b",
        "server": "37.139.42.151",
        "flag": "🇷🇺"
    },
    {
        "link": "tg://proxy?server=37.139.43.80&port=443&secret=ee4f6d6b6b6b6b6b6b6b6b6b6b6b6b6b",
        "server": "37.139.43.80",
        "flag": "🇷🇺"
    }
]

response = httpx.post(f"{WORKER_URL}/update", json={"proxies": test_proxies})
print(f"Статус: {response.status_code}")
print(f"Ответ: {response.json()}")
