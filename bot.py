import openai
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes
from config.settings import TELEGRAM_TOKEN, OPENAI_API_KEY, SESSION_DURATION
from utils.memory_manager import MemoryManager
import logging
from openai import OpenAIError
import sys
from utils.init_memory import init_memory_files
from utils.context_updater import update_history_context

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize FastAPI and Memory Manager
app = FastAPI()
memory_manager = MemoryManager()

# Add after the imports
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Add these variables after imports
DEFAULT_SESSION = 6 * 3600  # 6 hours
session_durations = {
    "short": 3 * 3600,  # 3 hours
    "medium": 6 * 3600,  # 6 hours
    "long": 12 * 3600   # 12 hours
}

async def get_chat_response(user_input: str) -> str:
    # Get context from memory
    short_term, history_context = memory_manager.get_context()
    
    # Prepare context for OpenAI
    history_context_text = "\n".join([fact["summary"] for fact in history_context]) if history_context else ""
    
    messages = [
        {"role": "system", "content": f"You are a helpful assistant. Important context:\n{history_context_text}"},
    ] + short_term + [{"role": "user", "content": user_input}]

    # Get response from OpenAI using new client format
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    assistant_response = response.choices[0].message.content
    
    # Update memory with new interaction
    memory_manager.update_memory(user_input, assistant_response)
    
    return assistant_response

# Telegram webhook endpoint
@app.post(f"/{TELEGRAM_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        update = Update.de_json(await request.json(), None)
        logger.debug(f"Received update: {update}")
        await application.update_queue.put(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        raise

# Message handler
async def message_handler(update: Update, context):
    try:
        logger.info(f"Received message: {update.message.text}")
        user_input = update.message.text
        response = await get_chat_response(user_input)
        logger.info(f"Sending response: {response}")
        await update.message.reply_text(response)
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("Sorry, I encountered an error while processing your request. Please try again later.")
    except Exception as e:
        logger.error(f"Error in message handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while processing your message.")

# Add these command handlers after the message_handler function
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm your AI assistant bot. I can help you with various tasks and maintain our conversation history.\n\n"
        "Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Here are the available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/clear - Clear conversation history\n"
        "/session - Set session duration"
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear short-term memory
    memory_manager._save_memory(SHORT_TERM_FILE, [])
    await update.message.reply_text("Conversation history has been cleared! 🧹")

# Add this command handler
async def set_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set session duration: /session [short|medium|long]"""
    try:
        duration = context.args[0].lower() if context.args else "medium"
        if duration in session_durations:
            global SESSION_DURATION
            SESSION_DURATION = session_durations[duration]
            await update.message.reply_text(
                f"Session duration set to {duration} ({SESSION_DURATION//3600} hours)"
            )
        else:
            await update.message.reply_text(
                "Invalid duration. Use: short (3h), medium (6h), or long (12h)"
            )
    except Exception as e:
        logger.error(f"Error in set_session_command: {e}")
        await update.message.reply_text("Error setting session duration")

# Update the application initialization section
async def setup_commands():
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show available commands"),
        BotCommand("clear", "Clear conversation history"),
        BotCommand("session", "Set session duration")
    ]
    await application.bot.set_my_commands(commands)

# Update the application handlers section
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("clear", clear_command))
application.add_handler(CommandHandler("session", set_session_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Update the main section
if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Initialize memory files
    init_memory_files()
    
    # Setup bot commands
    asyncio.run(setup_commands())
    
    # Start context updater in background
    asyncio.create_task(update_history_context())
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000) 