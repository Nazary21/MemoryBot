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

To update `history_context`, **GPT-3.5** is periodically used to analyze `mid-term` and generate key summaries.

### 3. **Technical Implementation**
**Tech Stack:**
- Python 3.9+
- FastAPI (to handle Telegram webhook and web dashboard)
- OpenAI API (GPT-3.5 for response generation)
- Python-Telegram-Bot (Telegram API integration)
- JSON files (for memory storage)
- Jinja2 Templates (for web dashboard)
- TailwindCSS (for dashboard styling)

#### **Bot Workflow:**
1. Telegram sends a message → server receives webhook.
2. The server analyzes `short_term` (messages from the last 6 hours).
3. `history_context` (key facts) is included in the prompt.
4. OpenAI API generates a response.
5. The response is stored in `short_term` and `whole_history`.
6. Older messages move to `mid-term`.
7. If `mid-term` exceeds 200 messages → GPT-3.5 generates a summary, updating `history_context`.

### 4. **Web Dashboard**
The bot includes a web interface for monitoring and management:
- **Status Monitoring:**
  - Telegram connection status
  - OpenAI API status
  - Memory statistics
- **Recent Messages Display:**
  - Shows latest conversations
  - Indicates user/bot messages
  - Includes timestamps
- **GPT Rules Management:**
  - Add/remove conversation rules
  - Categorize rules by type
  - Set rule priorities
- **API Configuration:**
  - Secure token management
  - Connection settings

### 5. **Deployment Options**
The developer considers **budget-friendly hosting solutions**:
- **Free options:** Google Cloud Run, Render, Railway (limited usage).
- **Affordable VPS:** Contabo ($5/month), Hetzner, DigitalOcean.
- **API cost optimization:** Using `GPT-3.5` instead of `GPT-4` to reduce expenses.

#### **Deploying the Server on VPS**
1. Install Python and FastAPI:
   ```sh
   sudo apt update
   sudo apt install python3 python3-pip
   pip install -r requirements.txt
   ```
2. Start the server:
   ```sh
   python bot.py
   ```
3. Connect Telegram Webhook:
   ```sh
   curl -F "url=https://server.com/{TOKEN}" https://api.telegram.org/bot{TOKEN}/setWebhook
   ```

### 6. **Dynamic Short-Term Memory Configuration**
The bot supports **adjustable session memory**:
- `set_session_duration("short")` → 3-hour short-term memory.
- `set_session_duration("medium")` → 6 hours (default).
- `set_session_duration("long")` → 12 hours.

### 7. **Bot Commands**
Available commands:
- `/start` - Start the bot
- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/session` - Set session duration
- `/analyze` - Analyze conversation history
- `/context` - Show historical context
- `/midterm` - Show mid-term memory stats
- `/shortterm` - Show short-term memory stats
- `/wholehistory` - Show whole history stats
- `/historycontext` - Show full history context

### 8. **History Analysis**
The bot includes periodic analysis of conversation history:
- Daily analysis of whole history
- Automatic summarization when history gets too large
- GPT-3.5 generates comprehensive summaries
- Results stored in `history_context`

Example analysis function:
```python
async def analyze_whole_history():
    whole_history = load_memory(WHOLE_HISTORY_FILE)
    history_text = "\n".join([msg["content"] for msg in whole_history])
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Create a concise summary of the conversation history."},
            {"role": "user", "content": history_text}
        ]
    )
    
    global_summary = response.choices[0].message.content
    save_memory(HISTORY_CONTEXT_FILE, [{"summary": global_summary}])
```

### 9. **OpenAI Response Generation**
The bot uses a structured approach to generate responses:
```python
async def get_chat_response(user_input: str) -> str:
    # Get context from memory
    short_term, history_context = memory_manager.get_context()
    
    # Format history context
    history_summary = "\n".join([fact["summary"] for fact in history_context]) if history_context else ""
    
    # Construct messages array
    messages = [
        {"role": "system", "content": f"""You are a helpful AI assistant with memory capabilities.
            Important context about our conversation history:
            {history_summary}
            
            Guidelines:
            - Remember and use people's names and preferences
            - Always respond in the same language as the user's message
            - Keep track of important information shared in conversation
            - If you learn someone's name, use it in future responses
            - Be friendly and personable while maintaining professionalism"""}
    ]
    
    # Add conversation history
    for msg in short_term:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Add current message
    messages.append({"role": "user", "content": user_input})
    
    # Get response from OpenAI
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    return response.choices[0].message.content
```

### 10. **Telegram Bot Initialization**
The bot uses a structured initialization process:
```python
# Initialize application
application = (ApplicationBuilder()
              .token(TELEGRAM_TOKEN)
              .concurrent_updates(True)
              .build())

async def init_application():
    try:
        # Initialize the application
        await application.initialize()
        await application.start()
        
        # Set up commands
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show available commands"),
            BotCommand("clear", "Clear conversation history"),
            BotCommand("session", "Set session duration"),
            BotCommand("analyze", "Analyze conversation history"),
            BotCommand("context", "Show historical context"),
            BotCommand("midterm", "Show mid-term memory stats"),
            BotCommand("shortterm", "Show short-term memory stats"),
            BotCommand("wholehistory", "Show whole history stats"),
            BotCommand("historycontext", "Show full history context")
        ]
        await application.bot.set_my_commands(commands)
        
        # Add message handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        return True
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        return False

### 11. **Security Considerations**
- Environment variables for sensitive data
- `.env` and `railway.json` kept local
- Template files for configuration
- Secure token handling in dashboard
- API key protection
- Git history cleaning for sensitive data
- Webhook token verification
- Error logging and sanitization
- Rate limiting and request validation