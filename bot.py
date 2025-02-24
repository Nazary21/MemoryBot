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
from contextlib import asynccontextmanager

# Setup logging first - move this to the very top, right after imports
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ],
    force=True  # This ensures our configuration takes precedence
)

# Create a logger for this module
logger = logging.getLogger(__name__)

# Also log third-party libraries we care about
logging.getLogger('uvicorn').setLevel(logging.INFO)
logging.getLogger('fastapi').setLevel(logging.INFO)
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('openai').setLevel(logging.INFO)

# Load environment variables
load_dotenv()
MOCK_MODE = str(os.getenv("MOCK_MODE", "false")).lower() in ("true", "1", "yes")

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize FastAPI
app = FastAPI(
    title="Telegram Bot API",
    description="FastAPI application for Telegram bot with memory capabilities",
    version="1.0.0"
)

# Add startup event handler
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting application initialization...")
        # Initialize memory files
        logger.info("Initializing memory files...")
        init_memory_files()
        
        # Initialize application
        logger.info("Running application initialization...")
        await init_application()
        
        # Start background tasks only if initialization successful
        if is_initialized:
            logger.info("Starting background tasks...")
            asyncio.create_task(update_history_context())
            asyncio.create_task(periodic_history_analysis())
            logger.info("Background tasks started")
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise

# Add shutdown event handler
@app.on_event("shutdown")
async def shutdown_event():
    try:
        logger.info("Starting application shutdown...")
        if application.running:
            await application.stop()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
        raise

# Initialize Memory Manager
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

# Move all command handlers to the top, before application initialization
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
        "/analyze - Analyze conversation history\n"
        "/context - Show historical context\n"
        "/midterm - Show mid-term memory stats\n"
        "/shortterm - Show short-term memory stats\n"
        "/wholehistory - Show whole history stats\n"
        "/historycontext - Show full history context"
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Clear short-term memory
        memory_manager._save_memory(SHORT_TERM_FILE, [])
        await update.message.reply_text("Conversation history has been cleared! 🧹")
    except Exception as e:
        logger.error(f"Error in clear_command: {e}", exc_info=True)
        await update.message.reply_text("Error clearing conversation history")

async def set_session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        logger.error(f"Error in set_session_command: {e}", exc_info=True)
        await update.message.reply_text("Error setting session duration")

async def analyze_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await analyze_whole_history()
        await update.message.reply_text("History analysis completed! The context has been updated.")
    except Exception as e:
        logger.error(f"Error in analyze_history_command: {e}", exc_info=True)
        await update.message.reply_text("Error analyzing history")

async def show_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(HISTORY_CONTEXT_FILE, 'r') as f:
            history_context = json.load(f)
        
        if not history_context:
            await update.message.reply_text("No historical context available yet.")
            return
            
        context_text = "📚 Historical Context:\n\n"
        for entry in history_context:
            context_text += f"🕒 {entry['timestamp'][:16]}\n"
            context_text += f"{entry['summary']}\n\n"
            
        await update.message.reply_text(context_text)
    except Exception as e:
        logger.error(f"Error showing context: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving historical context")

async def mid_term_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('memory/mid_term.json', 'r') as f:
            mid_term = json.load(f)
        
        stats = {
            "total_messages": len(mid_term),
            "user_messages": len([m for m in mid_term if m.get("role") == "user"]),
            "assistant_messages": len([m for m in mid_term if m.get("role") == "assistant"]),
            "time_range": f"{mid_term[0]['timestamp']} - {mid_term[-1]['timestamp']}" if mid_term else "No messages"
        }
        
        response = "📊 Mid-term Memory Stats:\n\n"
        response += f"Total messages: {stats['total_messages']}\n"
        response += f"User messages: {stats['user_messages']}\n"
        response += f"Assistant messages: {stats['assistant_messages']}\n"
        response += f"Time range: {stats['time_range']}"
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in mid_term_history_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving mid-term history stats")

async def short_term_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('memory/short_term.json', 'r') as f:
            short_term = json.load(f)
        
        stats = {
            "total_messages": len(short_term),
            "user_messages": len([m for m in short_term if m.get("role") == "user"]),
            "assistant_messages": len([m for m in short_term if m.get("role") == "assistant"]),
            "time_range": f"{short_term[0]['timestamp']} - {short_term[-1]['timestamp']}" if short_term else "No messages"
        }
        
        response = "📊 Short-term Memory Stats:\n\n"
        response += f"Total messages: {stats['total_messages']}\n"
        response += f"User messages: {stats['user_messages']}\n"
        response += f"Assistant messages: {stats['assistant_messages']}\n"
        response += f"Time range: {stats['time_range']}"
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in short_term_history_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving short-term history stats")

async def whole_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('memory/whole_history.json', 'r') as f:
            whole_history = json.load(f)
        
        stats = {
            "total_messages": len(whole_history),
            "user_messages": len([m for m in whole_history if m.get("role") == "user"]),
            "assistant_messages": len([m for m in whole_history if m.get("role") == "assistant"]),
            "time_range": f"{whole_history[0]['timestamp']} - {whole_history[-1]['timestamp']}" if whole_history else "No messages"
        }
        
        response = "📊 Whole History Stats:\n\n"
        response += f"Total messages: {stats['total_messages']}\n"
        response += f"User messages: {stats['user_messages']}\n"
        response += f"Assistant messages: {stats['assistant_messages']}\n"
        response += f"Time range: {stats['time_range']}"
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in whole_history_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving whole history stats")

async def history_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('memory/history_context.json', 'r') as f:
            history_context = json.load(f)
        
        if not history_context:
            await update.message.reply_text("No history context available")
            return
            
        response = "📝 History Context:\n\n"
        for entry in history_context:
            response += f"🕒 {entry['timestamp']}\n"
            response += f"Type: {entry['type']}\n"
            response += f"Messages: {entry.get('message_count', 'N/A')}\n"
            response += f"Summary:\n{entry['summary']}\n\n"
            
        if len(response) > 4000:
            response = response[:3997] + "..."
            
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in history_context_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving history context")

# Initialize Telegram application
logger.info("Initializing Telegram application...")
application = (ApplicationBuilder()
              .token(TELEGRAM_TOKEN)
              .concurrent_updates(True)
              .build())

# Track application state
is_initialized = False

# Message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        logger.info(f"Message handler called with input: {user_input}")
        logger.info(f"Chat ID: {update.message.chat_id}")
        logger.info(f"From user: {update.message.from_user.username}")
        
        logger.info("Getting chat response from OpenAI...")
        response = await get_chat_response(user_input)
        logger.info(f"Got OpenAI response: {response}")
        
        logger.info("Attempting to send message back to user...")
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=response
        )
        logger.info("Message sent successfully")
    except Exception as e:
        logger.error(f"Error in message handler: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text="An error occurred while processing your message."
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}", exc_info=True)

async def get_chat_response(user_input: str) -> str:
    try:
        logger.info("Starting get_chat_response...")
        # Get context from memory
        logger.info("Getting context from memory manager...")
        short_term, history_context = memory_manager.get_context()
        logger.info(f"Got short_term context with {len(short_term) if short_term else 0} messages")
        logger.info(f"Got history context with {len(history_context) if history_context else 0} entries")
        
        # Format history context
        history_summary = "\n".join([fact["summary"] for fact in history_context]) if history_context else ""
        
        # Start with system message
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
        
        # Add short-term memory - ensure proper string format
        if short_term:
            logger.info("Adding short-term memory to messages...")
            for msg in short_term:
                if isinstance(msg, dict):
                    # Extract string content from dict
                    content = msg.get("content")
                    if isinstance(content, dict):
                        content = content.get("content", "")
                    messages.append({"role": msg.get("role", "user"), "content": str(content)})
                else:
                    # Handle string messages
                    messages.append({"role": "user", "content": str(msg)})
        
        # Add current message
        messages.append({"role": "user", "content": user_input})
        
        if MOCK_MODE:
            logger.info("Mock mode enabled, returning mock response")
            return f"Mock response to: {user_input}"
            
        # Get response from OpenAI
        logger.info("Calling OpenAI API...")
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=messages
        )
        logger.info("Got response from OpenAI")
        
        assistant_response = response.choices[0].message.content
        
        # Store messages as proper format
        logger.info("Updating memory with new messages...")
        memory_manager.update_memory(
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": assistant_response}
        )
        logger.info("Memory updated successfully")
        
        return assistant_response
        
    except Exception as e:
        logger.error(f"Chat response error: {e}", exc_info=True)
        return "I apologize, but I encountered an error. Please try again."

# Test endpoint for OpenAI
@app.get("/test_openai")
async def test_openai():
    try:
        response = await get_chat_response("Hello, are you working?")
        return {"response": response}
    except Exception as e:
        logger.error(f"OpenAI test error: {e}", exc_info=True)
        return {"error": str(e)}

# Update the health check endpoint
@app.get("/")
async def health_check():
    try:
        if not is_initialized:
            return {"status": "initializing", "message": "Bot is starting up"}
        if not application.running:
            return {"status": "error", "message": "Bot is not running"}
        return {"status": "ok", "message": "Bot is running"}
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

# Update the application initialization section
async def init_application():
    try:
        global is_initialized
        if is_initialized:
            logger.info("Application already initialized")
            return
            
        logger.info("Initializing application...")
        await application.initialize()
        logger.info("Starting application...")
        await application.start()
        logger.info("Setting up commands...")
        await setup_commands()
        
        is_initialized = True
        logger.info("Application fully initialized and started")
    except Exception as e:
        logger.error(f"Error during application initialization: {e}", exc_info=True)
        raise

# Add the setup_commands function back
async def setup_commands():
    try:
        logger.info("Setting up bot commands...")
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
        logger.info("Bot commands set up successfully")
    except Exception as e:
        logger.error(f"Error setting up commands: {e}", exc_info=True)
        raise

# Add handlers after all functions are defined
logger.info("Adding handlers...")
try:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("session", set_session_command))
    application.add_handler(CommandHandler("analyze", analyze_history_command))
    application.add_handler(CommandHandler("context", show_context_command))
    application.add_handler(CommandHandler("midterm", mid_term_history_command))
    application.add_handler(CommandHandler("shortterm", short_term_history_command))
    application.add_handler(CommandHandler("wholehistory", whole_history_command))
    application.add_handler(CommandHandler("historycontext", history_context_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Handlers added successfully")
except Exception as e:
    logger.error(f"Error adding handlers: {e}", exc_info=True)
    raise

# Add back the webhook handler
@app.post("/{token:path}")
async def telegram_webhook(token: str, request: Request):
    try:
        logger.info("Webhook called - starting update processing")
        
        if not is_initialized:
            logger.error("Application not initialized yet")
            return {"error": "Application still initializing"}
        
        # Verify token
        if token != TELEGRAM_TOKEN:
            logger.error(f"Invalid token: {token}")
            return {"error": "Invalid token"}
            
        body = await request.json()
        logger.info(f"Received webhook body: {body}")
        
        # Create update object and process it
        logger.info("Creating Update object...")
        update = Update.de_json(body, application.bot)
        logger.info(f"Update object created successfully: {update}")
        
        if not update:
            logger.error("Failed to create Update object")
            return {"error": "Invalid update data"}
            
        if not application.bot:
            logger.error("Bot not initialized")
            return {"error": "Bot not initialized"}
            
        logger.info("Processing update through application...")
        try:
            logger.info("Calling process_update...")
            await application.process_update(update)
            logger.info("Update processed successfully")
        except Exception as process_error:
            logger.error(f"Error processing update: {process_error}", exc_info=True)
            # Try to send error message directly
            try:
                if update.message:
                    await application.bot.send_message(
                        chat_id=update.message.chat_id,
                        text="Sorry, I encountered an error processing your message."
                    )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}", exc_info=True)
            raise
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"error": str(e)}

# Update the main section
if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Get port from environment variable with fallback to 8000
    port = int(os.getenv("PORT", "8000"))
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["handlers"]["default"]["formatter"] = "default"
    log_config["loggers"]["uvicorn"]["level"] = "INFO"
    log_config["loggers"]["uvicorn.access"]["level"] = "INFO"
    
    logger.info("Starting application with configuration:")
    logger.info(f"Port: {port}")
    logger.info(f"Mock Mode: {MOCK_MODE}")
    logger.info(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'development')}")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        log_config=log_config,
        access_log=True
    )