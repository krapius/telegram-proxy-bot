// Telegram Proxy Bot - Cloudflare Worker
// Версия с кнопками, эндпоинтом /proxies и передачей chat_id в GitHub Actions

async function sendMessage(chatId, text, botToken, replyMarkup = null) {
  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  console.log(`📤 Отправка в чат ${chatId}, текст: ${text.substring(0, 50)}...`);
  
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true
  };
  if (replyMarkup) {
    body.reply_markup = replyMarkup;
  }
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const result = await response.json();
    console.log(`📥 Ответ от Telegram: ${JSON.stringify(result)}`);
    return result;
  } catch (err) {
    console.error("Ошибка sendMessage:", err);
    return null;
  }
}

async function editMessageText(chatId, messageId, text, botToken, replyMarkup = null) {
  const url = `https://api.telegram.org/bot${botToken}/editMessageText`;
  const body = {
    chat_id: chatId,
    message_id: messageId,
    text: text,
    parse_mode: "HTML"
  };
  if (replyMarkup) {
    body.reply_markup = replyMarkup;
  }
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    return await response.json();
  } catch (err) {
    console.error("Ошибка editMessageText:", err);
    return null;
  }
}

async function answerCallbackQuery(callbackQueryId, text, botToken) {
  const url = `https://api.telegram.org/bot${botToken}/answerCallbackQuery`;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        callback_query_id: callbackQueryId,
        text: text || "🔄 Обновляю..."
      })
    });
  } catch (err) {
    console.error("Ошибка answerCallbackQuery:", err);
  }
}

function createProxyButtons(proxies) {
  console.log("📋 Создаю кнопки для прокси:", JSON.stringify(proxies));
  const keyboard = [];
  for (let i = 0; i < Math.min(proxies.length, 6); i++) {
    const p = proxies[i];
    console.log(`Прокси #${i+1}: ${p.link}`);
    const flag = p.flag || "🇪🇺";
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(p.link)}`;
    
    keyboard.push([
      { text: `${flag} Прокси #${i + 1}`, url: p.link },
      { text: "📤", url: shareUrl }
    ]);
  }
  
  keyboard.push([{ text: "🔄 Обновить список прокси", callback_data: "refresh" }]);
  
  return { inline_keyboard: keyboard };
}

async function sendProxiesList(chatId, env, messageId = null) {
  console.log(`📞 sendProxiesList вызван для чата ${chatId}`);
  console.log(`🔑 Токен: ${env.TELEGRAM_BOT_TOKEN ? env.TELEGRAM_BOT_TOKEN.substring(0, 10) + '...' : 'undefined'}`);
  
  let proxies = [];
  try {
    const proxiesJson = await env.PROXY_KV.get("best_proxies");
    if (proxiesJson) {
      proxies = JSON.parse(proxiesJson);
      console.log(`📦 Найдено ${proxies.length} прокси в KV`);
    }
  } catch (err) {
    console.error("Ошибка чтения KV:", err);
  }
  
  const now = new Date();
  const formattedTime = `${now.getDate().toString().padStart(2, "0")}.${(now.getMonth() + 1).toString().padStart(2, "0")} ${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
  let text = `<b>🔥 Лучшие прокси SAMOLET на ${formattedTime}</b>`;
  
  if (!proxies || proxies.length === 0) {
    text += "\n❌ Нет доступных прокси.";
    const keyboard = { inline_keyboard: [[{ text: "🔄 Обновить список", callback_data: "refresh" }]] };
    if (messageId) {
      await editMessageText(chatId, messageId, text, env.TELEGRAM_BOT_TOKEN, keyboard);
    } else {
      await sendMessage(chatId, text, env.TELEGRAM_BOT_TOKEN, keyboard);
    }
    return;
  }
  
  const keyboard = createProxyButtons(proxies);
  console.log(`📋 Клавиатура создана`);
  
  if (messageId) {
    await editMessageText(chatId, messageId, text, env.TELEGRAM_BOT_TOKEN, keyboard);
  } else {
    await sendMessage(chatId, text, env.TELEGRAM_BOT_TOKEN, keyboard);
  }
}

async function handleCallback(query, env) {
  const chatId = query.message.chat.id;
  const data = query.data;
  
  console.log(`📥 Callback: ${data} от чата ${chatId}`);
  
  await answerCallbackQuery(query.id, "🔄 Запускаю обновление...", env.TELEGRAM_BOT_TOKEN);
  
  if (data === "refresh") {
    console.log(`📥 Callback refresh, GITHUB_TOKEN exists: ${!!env.GITHUB_TOKEN}`);
    
    const githubToken = env.GITHUB_TOKEN;
    if (githubToken) {
      console.log(`Token first 5 chars: ${githubToken.substring(0, 5)}...`);
      try {
        const response = await fetch('https://api.github.com/repos/krapius/telegram-proxy-bot/actions/workflows/update-proxies.yml/dispatches', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${githubToken}`,
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Telegram-Proxy-Bot/1.0 (https://t.me/migumBot)'
          },
          body: JSON.stringify({ 
            ref: 'main',
            inputs: {
              chat_id: chatId.toString()
            }
          })
        });
        console.log(`GitHub API response status: ${response.status}`);
        if (response.status === 204) {
          console.log('✅ GitHub Actions triggered successfully');
        } else {
          console.log(`⚠️ GitHub API returned ${response.status}`);
        }
      } catch (err) {
        console.error('❌ GitHub error:', err);
      }
    } else {
      console.log('❌ GITHUB_TOKEN not set in Worker environment');
    }
  }
}

async function handleWebhook(request, env) {
  try {
    const update = await request.json();
    console.log("📥 Получен webhook");
    
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
        await sendMessage(chatId, "🔄 <b>Обновление прокси начато!</b>\n\nЭто займёт 1-2 минуты...\nРезультат появится здесь автоматически.", env.TELEGRAM_BOT_TOKEN);
        
        const githubToken = env.GITHUB_TOKEN;
        if (githubToken) {
          try {
            await fetch('https://api.github.com/repos/krapius/telegram-proxy-bot/actions/workflows/update-proxies.yml/dispatches', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${githubToken}`,
                'Accept': 'application/vnd.github.v3+json',
              },
              body: JSON.stringify({ 
                ref: 'main',
                inputs: {
                  chat_id: chatId.toString()
                }
              })
            });
          } catch (err) {
            console.error('❌ Failed to trigger GitHub Actions:', err);
          }
        }
      } else if (text === "/status") {
        let proxiesCount = 0;
        try {
          const proxiesJson = await env.PROXY_KV.get("best_proxies");
          if (proxiesJson) {
            proxiesCount = JSON.parse(proxiesJson).length;
          }
        } catch (err) {}
        
        await sendMessage(chatId, `📊 <b>Статус бота</b>\n\n🟢 Worker: active\n📦 Прокси в кэше: ${proxiesCount}`, env.TELEGRAM_BOT_TOKEN);
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
  } catch (err) {}

  const html = `<!DOCTYPE html>
<html>
<head><title>Telegram Proxy Bot</title>
<style>
  body { font-family: system-ui; max-width: 800px; margin: 50px auto; padding: 20px; text-align: center; }
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
</body>
</html>`;
  return new Response(html, { headers: { "Content-Type": "text/html" } });
}

async function handleGetProxies(env) {
  const proxiesJson = await env.PROXY_KV.get("best_proxies");
  if (!proxiesJson) {
    return new Response(JSON.stringify({ proxies: [] }), { 
      headers: { "Content-Type": "application/json" } 
    });
  }
  return new Response(proxiesJson, { 
    headers: { "Content-Type": "application/json" } 
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
      headers: { "Content-Type": request.headers.get("Content-Type") || "application/json" },
      body: body,
    });
    const responseBody = await response.text();
    return new Response(responseBody, {
      status: response.status,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
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
    
    if (path === "/proxies") {
      return await handleGetProxies(env);
    }
    
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