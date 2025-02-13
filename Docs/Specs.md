**Discussion History on Deploying a Telegram Bot with Memory in Python**

### 1. **Project Idea**
The user wants to create a Telegram bot that utilizes **ChatGPT API** and retains conversation history. The memory should be structured and include:
- **Short-term memory (short-term)** – recent session messages.
- **Mid-term memory (mid-term)** – extended history (e.g., last 200 messages).
- **Full conversation history (whole_history)** – unfiltered storage of all messages.
- **Long-term context (history_context)** – key facts extracted from past conversations.

The bot will run on a server, process Telegram messages, and communicate with OpenAI API to generate responses.

### 2. **Memory Structure Development**
The memory is divided into four levels:
1. **Short-term** – includes only messages from the last **N hours**, rather than a fixed number of messages.
2. **Mid-term** – stores the **last 200 messages**, used for analyzing and improving `history_context`.
3. **Whole-history** – retains **all messages**.
4. **History-context** – a condensed version of the conversation with **important facts**.

To update `history_context`, **GPT-4** is periodically used to analyze `mid-term` and generate key summaries.

### 3. **Technical Implementation**
**Tech Stack:**
- Python 3.9+
- FastAPI (to handle Telegram webhook)
- OpenAI API (GPT-4 for response generation)
- Python-Telegram-Bot (Telegram API integration)
- JSON files (for memory storage)

#### **Bot Workflow:**
1. Telegram sends a message → server receives webhook.
2. The server analyzes `short_term` (messages from the last 6 hours).
3. `history_context` (key facts) is included in the prompt.
4. OpenAI API generates a response.
5. The response is stored in `short_term` and `whole_history`.
6. Older messages move to `mid-term`.
7. If `mid-term` exceeds 200 messages → GPT-4 generates a summary, updating `history_context`.

### 4. **Deployment Options**
The developer considers **budget-friendly hosting solutions**:
- **Free options:** Google Cloud Run, Render, Railway (limited usage).
- **Affordable VPS:** Contabo ($5/month), Hetzner, DigitalOcean.
- **API cost optimization:** Using `GPT-3.5` instead of `GPT-4` to reduce expenses.

#### **Deploying the Server on VPS**
1. Install Python and FastAPI:
   ```sh
   sudo apt update
   sudo apt install python3 python3-pip
   pip install openai fastapi uvicorn python-telegram-bot
   ```
2. Start the server:
   ```sh
   python bot.py
   ```
3. Connect Telegram Webhook:
   ```sh
   curl -F "url=https://server.com/{TOKEN}" https://api.telegram.org/bot{TOKEN}/setWebhook
   ```

Telegram bot token: 8050570051:AAG4byICXKPopJ4pkngSfXLBEa7ZnJ4eTrs

### 5. **Dynamic Short-Term Memory Configuration**
The bot supports **adjustable session memory**:
- `set_session_duration("short")` → 3-hour short-term memory.
- `set_session_duration("medium")` → 6 hours (default).
- `set_session_duration("long")` → 12 hours.

### 6. **Implementation Code (bot.py)**
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


### 7. **Conclusion**
This solution enables the Telegram bot to efficiently **retain conversation memory** without overwhelming the model with unnecessary data. The memory system is **flexible and scalable**, making it suitable for future enhancements.

This document can now be provided to Cursor.com for implementation.




###8. Add analysis of  whole_history for improving of history_context?
once a day or when whole_history gets to big, we can analyse whole history and make a new summary of history_context

example: 

def analyze_whole_history():
    whole_history = load_memory(WHOLE_HISTORY_FILE)
    history_context = load_memory(HISTORY_CONTEXT_FILE)

    # Сливаем всю историю в один текст
    history_text = "\n".join([msg["content"] for msg in whole_history])

    # Запрашиваем GPT-4 создать глобальное резюме
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Создай краткий пересказ всей истории общения."},
            {"role": "user", "content": history_text}
        ]
    )

    global_summary = response["choices"][0]["message"]["content"]

    # Очищаем старый `history_context` и записываем обновлённый
    save_memory(HISTORY_CONTEXT_FILE, [{"summary": global_summary}])