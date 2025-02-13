import os
import openai
import time
import json
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Настройки
TOKEN = "твой_телеграм_токен"
OPENAI_API_KEY = "твой_openai_ключ"

# Файлы памяти
SHORT_TERM_FILE = "short_term.json"
MID_TERM_FILE = "mid_term.json"
WHOLE_HISTORY_FILE = "whole_history.json"
HISTORY_CONTEXT_FILE = "history_context.json"

SESSION_DURATION = 6 * 3600  # 6 часов

# Функции загрузки и сохранения памяти
def load_memory(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_memory(file, data):
    with open(file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Обновление краткосрочной памяти по времени
def update_short_term_memory(user_input, assistant_response):
    short_memory = load_memory(SHORT_TERM_FILE)
    mid_memory = load_memory(MID_TERM_FILE)
    whole_history = load_memory(WHOLE_HISTORY_FILE)

    current_time = time.time()

    short_memory.append({"role": "user", "content": user_input, "timestamp": current_time})
    short_memory.append({"role": "assistant", "content": assistant_response, "timestamp": current_time})
    whole_history.append({"role": "user", "content": user_input, "timestamp": current_time})
    whole_history.append({"role": "assistant", "content": assistant_response, "timestamp": current_time})

    short_memory = [msg for msg in short_memory if current_time - msg["timestamp"] <= SESSION_DURATION]
    moved_to_mid = [msg for msg in short_memory if current_time - msg["timestamp"] > SESSION_DURATION]
    
    if moved_to_mid:
        mid_memory.extend(moved_to_mid)

    save_memory(SHORT_TERM_FILE, short_memory)
    save_memory(MID_TERM_FILE, mid_memory)
    save_memory(WHOLE_HISTORY_FILE, whole_history)

# Получение ответа от OpenAI
def get_chat_response(user_input):
    short_memory = load_memory(SHORT_TERM_FILE)
    history_context = load_memory(HISTORY_CONTEXT_FILE)

    context_messages = short_memory
    history_context_text = "\n".join([fact["summary"] for fact in history_context])

    messages = [
        {"role": "system", "content": "Ты умный ассистент. Важные факты:\n" + history_context_text},
    ] + context_messages + [{"role": "user", "content": user_input}]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        api_key=OPENAI_API_KEY
    )

    assistant_response = response["choices"][0]["message"]["content"]
    update_short_term_memory(user_input, assistant_response)

    return assistant_response

# Инициализация Telegram бота
app = FastAPI()

@app.post(f"/{TOKEN}")
async def telegram_webhook(request: Request):
    update = Update.de_json(await request.json(), bot)
    await application.update_queue.put(update)
    return {"status": "ok"}

async def message_handler(update: Update, context):
    user_input = update.message.text
    response = get_chat_response(user_input)
    await update.message.reply_text(response)

# Запуск бота
application = Application.builder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
