import openai
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
from config.settings import TELEGRAM_TOKEN, OPENAI_API_KEY, SESSION_DURATION, HISTORY_CONTEXT_FILE
from utils.memory_manager import MemoryManager
import logging
from openai import OpenAIError
import sys
from utils.init_memory import init_memory_files
from utils.context_updater import update_history_context
from utils.whole_history_analyzer import periodic_history_analysis, analyze_whole_history
import asyncio
import os
from dotenv import load_dotenv
import json

# Setup logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MOCK_MODE = str(os.getenv("MOCK_MODE", "false")).lower() in ("true", "1", "yes")

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize FastAPI and Memory Manager
app = FastAPI()
memory_manager = MemoryManager()

# Add these variables after imports
DEFAULT_SESSION = 6 * 3600  # 6 hours
session_durations = {
    "short": 3 * 3600,  # 3 hours
    "medium": 6 * 3600,  # 6 hours
    "long": 12 * 3600   # 12 hours
}

# Add after other constants
logger.info(f"MOCK_MODE is set to: {MOCK_MODE}")

async def get_chat_response(user_input: str) -> str:
    if MOCK_MODE:
        return f"Mock response to: {user_input}"
        
    messages = [
        {"role": "system", "content": """You are a helpful assistant with specific traits:
            1. You maintain conversation history and context
            2. You work in group of people, you know names of people you are talking to, you know relations between them
            3. You know a lot of interesting facts about people you are talking to
            4. You can analyze and summarize past conversations
            5. You adapt your responses based on user preferences
            6. You help with various tasks while maintaining a friendly tone
            7. You remember important details about the user
            
            Important guidelines:
            - Always reply in a language of the  user and remember his last language used for new conversation
            - Keep responses concise but informative
            - Use emojis occasionally to add warmth
            - If context is unclear, politely ask for clarification
            - Reference relevant past conversations when appropriate
            """},
        {"role": "user", "content": user_input}
    ]
    
    # OpenAI's client is synchronous, we should run it in a thread pool
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    return response.choices[0].message.content

# Test endpoint for OpenAI
@app.get("/test_openai")
async def test_openai():
    try:
        response = await get_chat_response("Hello, are you working?")
        return {"response": response}
    except Exception as e:
        logger.error(f"OpenAI test error: {e}", exc_info=True)
        return {"error": str(e)}

# Message handler
async def message_handler(update: Update, context):
    try:
        user_input = update.message.text
        logger.info(f"Processing message: {user_input}")
        response = await get_chat_response(user_input)
        logger.info(f"Got response: {response}")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in message handler: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while processing your message.")

# Webhook handler
@app.post(f"/{TELEGRAM_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        
        # Create update object
        update = Update.de_json(body, application.bot)  # Changed None to application.bot
        logger.info(f"Created update object: {update}")
        
        # Process update directly instead of using queue
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise

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
        "/session - Set session duration\n"
        "/analyze - Analyze entire conversation history\n"
        "/context - Show current historical context"
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

# Add this command handler
async def analyze_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger history analysis"""
    try:
        await analyze_whole_history()
        await update.message.reply_text("History analysis completed! The context has been updated.")
    except Exception as e:
        logger.error(f"Error in analyze_history_command: {e}")
        await update.message.reply_text("Error analyzing history")

# Add this command handler
async def show_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current historical context"""
    try:
        with open(HISTORY_CONTEXT_FILE, 'r') as f:
            history_context = json.load(f)
        
        if not history_context:
            await update.message.reply_text("No historical context available yet.")
            return
            
        # Format the context nicely
        context_text = "📚 Historical Context:\n\n"
        for entry in history_context:
            context_text += f"🕒 {entry['timestamp'][:16]}\n"  # Show date/time
            context_text += f"{entry['summary']}\n\n"
            
        await update.message.reply_text(context_text)
    except Exception as e:
        logger.error(f"Error showing context: {e}")
        await update.message.reply_text("Error retrieving historical context")

# Update the application initialization section
async def setup_commands():
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show available commands"),
        BotCommand("clear", "Clear conversation history"),
        BotCommand("session", "Set session duration"),
        BotCommand("analyze", "Analyze conversation history"),
        BotCommand("context", "Show historical context")
    ]
    await application.bot.set_my_commands(commands)

# Update the main section
if __name__ == "__main__":
    import uvicorn
    import asyncio
    from contextlib import asynccontextmanager
    
    # Initialize application at module level
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialize memory files
        init_memory_files()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("session", set_session_command))
        application.add_handler(CommandHandler("analyze", analyze_history_command))
        application.add_handler(CommandHandler("context", show_context_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        # Start the application
        await application.initialize()
        await application.start()
        
        # Setup bot commands
        await setup_commands()
        
        # Start background tasks
        asyncio.create_task(update_history_context())
        asyncio.create_task(periodic_history_analysis())
        
        yield
        
        # Cleanup
        await application.stop()
    
    app.router.lifespan_context = lifespan
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug") 