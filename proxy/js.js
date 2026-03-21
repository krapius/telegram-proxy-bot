// Telegram Proxy Bot - Cloudflare Worker
// Полная версия с логированием и KV Storage

async function sendMessage(chatId, text, botToken) {
  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  const body = JSON.stringify({
    chat_id: chatId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true
  });
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body
    });
    return await response.json();
  } catch (err) {
    console.error("Ошибка sendMessage:", err);
    return null;
  }
}

async function sendProxiesList(chatId, env) {
  console.log(`📤 sendProxiesList для чата ${chatId}`);
  
  let proxies = [];
  try {
    const proxiesJson = await env.PROXY_KV.get("best_proxies");
    if (proxiesJson) {
      proxies = JSON.parse(proxiesJson);
      console.log(`📦 Найдено ${proxies.length} прокси в KV`);
    } else {
      console.log('⚠️ Прокси не найдены в KV');
    }
  } catch (err) {
    console.error("Ошибка чтения KV:", err);
  }
  
  const now = new Date();
  const formattedTime = `${now.getDate().toString().padStart(2, "0")}.${(now.getMonth() + 1).toString().padStart(2, "0")} ${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
  let text = `<b>🔥 Лучшие прокси SAMOLET на ${formattedTime}</b>\n\n`;
  
  if (!proxies || proxies.length === 0) {
    text += "❌ Нет доступных прокси.\n\nНажмите /refresh для обновления.";
  } else {
    for (let i = 0; i < Math.min(proxies.length, 6); i++) {
      const p = proxies[i];
      const flag = p.flag || "🌍";
      text += `${flag} <b>Прокси #${i + 1}</b>\n`;
      text += `<code>${p.link}</code>\n\n`;
    }
    text += `\n🔄 <i>Обновляется автоматически каждые 6 часов</i>`;
  }
  
  const keyboard = {
    inline_keyboard: [[{ text: "🔄 Обновить список", callback_data: "refresh" }]]
  };
  
  const url = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  const body = JSON.stringify({
    chat_id: chatId,
    text: text,
    parse_mode: "HTML",
    reply_markup: keyboard,
    disable_web_page_preview: true
  });
  
  console.log(`📨 Отправка в Telegram, chat_id: ${chatId}`);
  console.log(`📨 URL: ${url}`);
  console.log(`📨 Текст сообщения: ${text.substring(0, 100)}...`);
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body
    });
    const result = await response.json();
    console.log(`📨 Ответ от Telegram:`, JSON.stringify(result));
    console.log(`📨 Сообщение отправлено в чат ${chatId}, результат: ${result.ok ? 'OK' : 'ERROR'}`);
    if (!result.ok) {
      console.log(`📨 Ошибка: ${result.description}`);
    }
  } catch (err) {
    console.error("Ошибка sendProxiesList:", err);
  }
}

async function sendStatus(chatId, env) {
  let proxiesCount = 0;
  let lastUpdate = "никогда";
  try {
    const proxiesJson = await env.PROXY_KV.get("best_proxies");
    if (proxiesJson) {
      proxiesCount = JSON.parse(proxiesJson).length;
    }
    const lastUpdateRaw = await env.PROXY_KV.get("last_update");
    if (lastUpdateRaw) {
      lastUpdate = lastUpdateRaw;
    }
  } catch (err) {
    console.error("Ошибка чтения KV:", err);
  }
  
  const text = `
📊 <b>Статус бота</b>

🟢 Worker: active
📦 Прокси в кэше: ${proxiesCount}
🕐 Последнее обновление: ${lastUpdate}
  `;
  await sendMessage(chatId, text, env.TELEGRAM_BOT_TOKEN);
}

async function handleCallback(query, env) {
  const chatId = query.message.chat.id;
  const data = query.data;
  
  const answerUrl = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/answerCallbackQuery`;
  await fetch(answerUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      callback_query_id: query.id,
      text: "🔄 Обновляю..."
    })
  });
  
  if (data === "refresh") {
    await sendMessage(chatId, "🔄 <b>Обновление прокси начато!</b>\n\nРезультат появится через несколько минут.", env.TELEGRAM_BOT_TOKEN);
  }
}

async function handleWebhook(request, env) {
  try {
    const update = await request.json();
    console.log("📥 Получен webhook:", JSON.stringify(update).slice(0, 200));
    
    if (update.callback_query) {
      await handleCallback(update.callback_query, env);
      return new Response("OK", { status: 200 });
    }
    
    if (update.message) {
      const msg = update.message;
      const chatId = msg.chat.id;
      const text = msg.text || "";
      console.log(`📝 Команда: ${text} от чата ${chatId}`);
      
      if (text === "/start") {
        await sendProxiesList(chatId, env);
      } else if (text === "/refresh") {
        await sendMessage(chatId, "🔄 <b>Обновление прокси начато!</b>\n\nЭто может занять 1-2 минуты.", env.TELEGRAM_BOT_TOKEN);
      } else if (text === "/status") {
        await sendStatus(chatId, env);
      } else if (text && text.startsWith("/")) {
        await sendMessage(chatId, "❓ Неизвестная команда\n\nДоступные:\n/start - список прокси\n/refresh - обновить\n/status - статус", env.TELEGRAM_BOT_TOKEN);
      }
    }
    
    return new Response("OK", { status: 200 });
  } catch (err) {
    console.error("Ошибка webhook:", err);
    return new Response("Error: " + err.message, { status: 500 });
  }
}

async function handleUpdate(request, env) {
  try {
    const data = await request.json();
    if (!data.proxies) {
      return new Response(JSON.stringify({ ok: false, error: "No proxies data" }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      });
    }
    await env.PROXY_KV.put("best_proxies", JSON.stringify(data.proxies));
    await env.PROXY_KV.put("last_update", new Date().toISOString());
    console.log(`✅ Обновлено ${data.proxies.length} прокси в KV`);
    return new Response(JSON.stringify({ ok: true, count: data.proxies.length }), {
      headers: { "Content-Type": "application/json" }
    });
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

async function handleStatus(env) {
  let proxiesCount = 0;
  let lastUpdate = "никогда";
  try {
    const proxiesJson = await env.PROXY_KV.get("best_proxies");
    if (proxiesJson) {
      proxiesCount = JSON.parse(proxiesJson).length;
    }
    const lastUpdateRaw = await env.PROXY_KV.get("last_update");
    if (lastUpdateRaw) {
      lastUpdate = lastUpdateRaw;
    }
  } catch (err) {
    console.error("Ошибка чтения KV:", err);
  }
  
  const html = `<!DOCTYPE html>
<html>
<head>
  <title>Telegram Proxy Bot</title>
  <style>
    body { font-family: system-ui; max-width: 800px; margin: 50px auto; padding: 20px; text-align: center; }
    h1 { color: #2c3e50; }
    .status { background: #27ae60; color: white; padding: 10px 20px; border-radius: 8px; display: inline-block; }
    .info { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px; text-align: left; }
  </style>
</head>
<body>
  <h1>🤖 Telegram Proxy Bot</h1>
  <p><span class="status">🟢 Running</span></p>
  <div class="info">
    <p><strong>📊 Статистика:</strong></p>
    <p>• Прокси в кэше: ${proxiesCount}</p>
    <p>• Последнее обновление: ${lastUpdate}</p>
    <p>• Бот: <a href="https://t.me/migumBot">@migumBot</a></p>
  </div>
  <hr>
  <p><small>Cloudflare Worker | ${new Date().toISOString()}</small></p>
</body>
</html>`;
  return new Response(html, {
    headers: { "Content-Type": "text/html" }
  });
}

async function proxyToTelegram(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
  const telegramUrl = `https://api.telegram.org${path}`;
  
  try {
    let body = null;
    if (request.method !== "GET" && request.method !== "HEAD") {
      body = await request.text();
    }
    const response = await fetch(telegramUrl, {
      method: request.method,
      headers: {
        "Content-Type": request.headers.get("Content-Type") || "application/json",
      },
      body: body,
    });
    const responseBody = await response.text();
    return new Response(responseBody, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    if (path.startsWith("/bot")) {
      return await proxyToTelegram(request, env);
    }
    if (request.method === "POST" && path === "/update") {
      return await handleUpdate(request, env);
    }
    if (request.method === "POST") {
      return await handleWebhook(request, env);
    }
    return await handleStatus(env);
  }
};