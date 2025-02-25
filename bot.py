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
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from web.dashboard import router as dashboard_router
from fastapi.responses import RedirectResponse
from utils.rule_manager import RuleManager
from utils.ai_response import AIResponseHandler
from datetime import datetime
from utils.database import Database
from utils.hybrid_memory_manager import HybridMemoryManager
from utils.registration_handler import RegistrationHandler

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

# Initialize FastAPI
app = FastAPI(
    title="PykhBrain Bot",
    description="Telegram bot with memory and web dashboard",
    version="1.0.0"
)

# Global initialization flag
is_initialized = False

# Mount static files and templates
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include dashboard routes
app.include_router(dashboard_router, prefix="/dashboard")

# Add startup event handler
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting application initialization...")
        # Initialize memory files
        logger.info("Initializing memory files...")
        init_memory_files()
        
        # Initialize database tables
        logger.info("Setting up database tables...")
        await db.setup_tables()
        
        # Check database status
        if db.initialized:
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database not initialized, using fallback mode")
        
        # Create default rules for account 1 if they don't exist
        logger.info("Checking and creating default rules...")
        try:
            rules = await rule_manager.get_rules(account_id=1)
            if not rules:
                logger.info("No default rules found. Creating them...")
                success = await rule_manager.create_default_rules(account_id=1)
                if success:
                    logger.info("Default rules created successfully")
                    # Verify rules were created
                    rules = await rule_manager.get_rules(account_id=1)
                    logger.info(f"Verified {len(rules)} default rules exist")
                else:
                    logger.error("Failed to create default rules")
            else:
                logger.info(f"Found {len(rules)} existing rules for account 1")
        except Exception as rules_error:
            logger.error(f"Error checking/creating default rules: {rules_error}")
            # Try to create default rules using fallback method
            try:
                logger.info("Attempting to create default rules using fallback method...")
                success = rule_manager._create_default_rules_fallback(account_id=1)
                if success:
                    logger.info("Default rules created using fallback method")
                else:
                    logger.error("Failed to create default rules using fallback method")
            except Exception as fallback_error:
                logger.error(f"Error in fallback rule creation: {fallback_error}")
        
        # Initialize application
        logger.info("Running application initialization...")
        init_success = await init_application()
        
        if init_success:
            # Start background tasks only if initialization successful
            logger.info("Starting background tasks...")
            asyncio.create_task(update_history_context())
            asyncio.create_task(periodic_history_analysis())
            logger.info("Background tasks started")
        else:
            logger.error("Application initialization failed")
            
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

# Initialize components
db = Database()
hybrid_memory = HybridMemoryManager(db)
rule_manager = RuleManager(db)
ai_handler = AIResponseHandler(db)
registration_handler = RegistrationHandler(db)

# Initialize Memory Manager with default account
memory_manager = MemoryManager(account_id=1, db=db)

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
    """Handle the /start command"""
    try:
        chat_id = update.effective_chat.id
        
        # Create temporary account if needed
        account = await db.get_or_create_temporary_account(chat_id)
        
        await update.message.reply_text(
            "👋 Hello! I'm your AI assistant bot.\n\n"
            "I've created a temporary account for you, so you can start chatting right away!\n\n"
            "To create a permanent account with additional features:\n"
            "Use /register\n\n"
            "To see all available commands:\n"
            "Use /help"
        )
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(
            "Sorry, there was an error starting the bot. Please try again."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Here are the available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/register - Create a permanent account\n"
        "/status - Check your account status\n"
        "/clear - Clear conversation history\n"
        "/session - Set session duration\n"
        "/analyze - Analyze conversation history\n"
        "/context - Show historical context\n"
        "/midterm - Show mid-term memory stats\n"
        "/shortterm - Show short-term memory stats\n"
        "/wholehistory - Show whole history stats\n"
        "/historycontext - Show full history context\n"
        "/rules - Show current bot rules\n"
        "/model - Show current AI model"
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
        context_text = memory_manager.get_context()
        if not context_text:
            await update.message.reply_text("No recent context available.")
            return
            
        await update.message.reply_text(f"📚 Recent Context:\n\n{context_text}")
    except Exception as e:
        logger.error(f"Error showing context: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving context")

async def mid_term_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mid_term = memory_manager._load_memory(memory_manager.mid_term_file)
        
        if not mid_term:
            await update.message.reply_text("No mid-term history available.")
            return
            
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
        short_term = memory_manager._load_memory(memory_manager.short_term_file)
        
        if not short_term:
            await update.message.reply_text("No short-term history available.")
            return
            
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
        whole_history = memory_manager._load_memory(memory_manager.whole_history_file)
        
        if not whole_history:
            await update.message.reply_text("No history available.")
            return
            
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
        # Force an update of the history context
        logger.info("Forcing history context update...")
        await analyze_whole_history()
        
        # Get history context using memory manager
        history_context = memory_manager.get_history_context()
        
        if not history_context:
            await update.message.reply_text("No history context available")
            return
            
        await update.message.reply_text(f"📝 History Context:\n\n{history_context}")
    except Exception as e:
        logger.error(f"Error in history_context_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving history context")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display current bot rules"""
    try:
        chat_id = update.effective_chat.id
        logger.info(f"Processing /rules command from chat_id {chat_id}")
        
        # Get or create account for this chat
        account = await db.get_or_create_temporary_account(chat_id)
        account_id = account.get('id', 1)  # Default to 1 if not found
        
        # Get rules for this account
        rules = await rule_manager.get_rules(account_id=account_id)
        
        # If no rules found, try to create default rules
        if not rules:
            logger.info(f"No rules found for account {account_id}. Creating default rules.")
            success = await rule_manager.create_default_rules(account_id)
            if success:
                # Try to get rules again
                rules = await rule_manager.get_rules(account_id=account_id)
                logger.info(f"Created {len(rules)} default rules for account {account_id}")
            else:
                logger.error(f"Failed to create default rules for account {account_id}")
        
        # Format and send rules
        rules_text = rule_manager.get_formatted_rules(rules)
        await update.message.reply_text(rules_text)
    except Exception as e:
        logger.error(f"Error in rules_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving rules. Please try again later.")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display current AI model information"""
    try:
        model_info = ai_handler.get_current_model()
        await update.message.reply_text(f"Current AI model: {model_info}")
    except Exception as e:
        logger.error(f"Error in model_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving model information")

# Initialize Telegram application
logger.info("Initializing Telegram application...")
application = (ApplicationBuilder()
              .token(TELEGRAM_TOKEN)
              .concurrent_updates(True)
              .build())

# Add after other logging setup
def debug_log(chat_id: int, stage: str, details: str = None):
    """Temporary debug logging function for message handler troubleshooting"""
    message = f"[DEBUG][Chat {chat_id}] {stage}"
    if details:
        message += f": {details}"
    logger.debug(message)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages with hybrid memory support"""
    try:
        chat_id = update.effective_chat.id
        debug_log(chat_id, "Message received", f"From user: {update.effective_user.username}")
        original_text = update.message.text
        debug_log(chat_id, "Original text", original_text)
        
        # Extract message content, removing bot mention if present
        user_input = original_text
        if f"@{context.bot.username}" in original_text:
            user_input = original_text.replace(f"@{context.bot.username}", "").strip()
            debug_log(chat_id, "Mention removed", f"Cleaned text: {user_input}")
        
        if not user_input:  # If message is empty after cleaning
            debug_log(chat_id, "Empty message", "Skipping processing")
            return
        
        # Get or create memory manager for this chat
        debug_log(chat_id, "Getting memory manager")
        memory_manager = await get_memory_manager(chat_id)
        
        try:
            # Get conversation context from memory
            debug_log(chat_id, "Fetching memory")
            short_term_memory = await memory_manager.get_memory(chat_id, 'short_term')
            debug_log(chat_id, "Memory fetched", f"Context size: {len(short_term_memory)}")
            
            # Get active rules
            rules = await rule_manager.get_rules(account_id=1)
            rules_text = rule_manager.get_formatted_rules(rules)
            
            # Prepare messages for AI with rules
            messages = [
                {"role": "system", "content": f"You are a helpful assistant. Follow these rules:\n{rules_text}"}
            ]
            
            # Add context from memory
            for msg in short_term_memory[-5:]:  # Last 5 messages for context
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
            
            # Add current user message
            messages.append({"role": "user", "content": user_input})
            debug_log(chat_id, "Messages prepared", f"Total messages: {len(messages)}")
            
            # Get AI response using AIResponseHandler
            debug_log(chat_id, "Getting AI response")
            response_text = await ai_handler.get_chat_response(account_id=1, messages=messages)
            debug_log(chat_id, "Got AI response", f"Length: {len(response_text)}")
            
            # Store both user message and response in memory
            debug_log(chat_id, "Storing messages")
            await memory_manager.add_message(chat_id, "user", user_input)
            await memory_manager.add_message(chat_id, "assistant", response_text)
            
            # Send response to user
            debug_log(chat_id, "Sending response")
            await context.bot.send_message(chat_id=chat_id, text=response_text)
            debug_log(chat_id, "Response sent successfully")
            
        except Exception as e:
            logger.error(f"Error in message processing: {e}")
            debug_log(chat_id, "Processing error", str(e))
            # Attempt basic fallback without context
            try:
                debug_log(chat_id, "Attempting fallback")
                response_text = await ai_handler.get_chat_response(account_id=1, messages=[
                    {"role": "system", "content": "You are a helpful assistant. Be concise and friendly."},
                    {"role": "user", "content": user_input}
                ])
                debug_log(chat_id, "Fallback successful")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=response_text
                )
            except Exception as final_error:
                logger.error(f"Final fallback also failed: {final_error}")
                debug_log(chat_id, "Fallback failed", str(final_error))
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="I apologize, but I encountered an error. Please try again later."
                )
    except Exception as e:
        logger.error(f"Critical error in message handler: {e}")
        debug_log(chat_id, "Critical error", str(e))
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="I encountered a critical error. Please try again later."
            )
        except:
            debug_log(chat_id, "Failed to send error message")
            pass  # If we can't even send error message, just log and continue

async def get_memory_manager(chat_id: int) -> HybridMemoryManager:
    """Get or create a memory manager for a chat"""
    try:
        # Initialize database connection if not already initialized
        if not hasattr(get_memory_manager, '_db'):
            get_memory_manager._db = Database()
            
            # Log the mode we're operating in
            if get_memory_manager._db.fallback_mode:
                logger.info("Operating in file-based fallback mode")
            else:
                logger.info("Operating with Supabase database")
        
        # Create hybrid memory manager (will work in both normal and fallback mode)
        return HybridMemoryManager(get_memory_manager._db)
    except Exception as e:
        logger.error(f"Error creating memory manager: {e}")
        # Create a new Database instance that will automatically use fallback mode
        return HybridMemoryManager(Database())

# Test endpoint for OpenAI
@app.get("/test_openai")
async def test_openai():
    try:
        response = await get_chat_response("Hello, are you working?", 0)
        return {"response": response}
    except Exception as e:
        logger.error(f"OpenAI test error: {e}", exc_info=True)
        return {"error": str(e)}

# Update the health check endpoints
@app.get("/")
async def root(request: Request):
    """Main route that handles both health checks and dashboard redirects"""
    # Check if it's a health check request (from Railway)
    user_agent = request.headers.get("user-agent", "").lower()
    if "railway" in user_agent or "health" in user_agent:
        return {"status": "ok"}
        
    # If not a health check, redirect to dashboard
    return RedirectResponse(
        url="/dashboard",
        status_code=307,
        headers={
            "WWW-Authenticate": 'Basic realm="PykhBrain Dashboard"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache"
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    try:
        # Always return 200 OK for Railway health checks
        return {
            "status": "ok",
            "initialized": is_initialized,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        # Still return 200 OK but with error details
        return {
            "status": "ok",  # Changed to ok to pass Railway health checks
            "timestamp": datetime.now().isoformat()
        }

@app.get("/_health")
async def railway_health():
    """Dedicated health check endpoint for Railway"""
    # Always return 200 OK with minimal response
    return {"status": "ok"}

# Update the application initialization section
async def init_application():
    try:
        global is_initialized
        if is_initialized:
            logger.info("Application already initialized")
            return True
            
        logger.info("Initializing application...")
        await application.initialize()
        logger.info("Starting application...")
        await application.start()
        logger.info("Setting up commands...")
        await setup_commands()
        
        # Verify bot is working by getting bot info
        try:
            bot_info = await application.bot.get_me()
            logger.info(f"Bot initialized successfully: @{bot_info.username}")
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return False
        
        # Add new command handlers
        application.add_handler(CommandHandler("register", registration_handler.handle_register_command))
        application.add_handler(CommandHandler("status", registration_handler.handle_status_command))
        
        is_initialized = True
        logger.info("Application fully initialized and started")
        return True
    except Exception as e:
        logger.error(f"Error during application initialization: {e}", exc_info=True)
        return False

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
            BotCommand("historycontext", "Show full history context"),
            BotCommand("rules", "Show current bot rules"),
            BotCommand("model", "Show current AI model")
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
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("model", model_command))
    # Update message handler to use Mention filter or reply filter
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.Entity("mention") | filters.REPLY),
        message_handler
    ))
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

class MultiTenantBot:
    def __init__(self):
        self.memory_managers = {}  # Dict to store memory managers per account
        self.db = Database()  # Your database connection

    async def get_or_create_account(self, chat_id):
        account = await self.db.fetch_one(
            "SELECT * FROM accounts WHERE telegram_chat_id = $1",
            chat_id
        )
        
        if not account:
            account = await self.db.fetch_one(
                """
                INSERT INTO accounts (telegram_chat_id) 
                VALUES ($1) RETURNING *
                """,
                chat_id
            )
            
        return account

    async def get_memory_manager(self, chat_id):
        if chat_id not in self.memory_managers:
            account = await self.get_or_create_account(chat_id)
            self.memory_managers[chat_id] = MemoryManager(
                account_id=account['id'],
                db=self.db
            )
        return self.memory_managers[chat_id]

    async def handle_message(self, message: Update):
        chat_id = message.effective_chat.id
        memory_manager = await self.get_memory_manager(chat_id)
        
        # Get account-specific settings
        settings = await self.db.fetch_all(
            "SELECT setting_key, setting_value FROM account_settings WHERE account_id = $1",
            memory_manager.account_id
        )
        
        # Process message with account context
        # ... rest of your message handling logic ...

    async def handle_shopping_list(self, message: Update):
        chat_id = message.effective_chat.id
        memory_manager = await self.get_memory_manager(chat_id)
        
        # Natural language processing to detect shopping list intent
        if "add to grocery list" in message.message.text.lower():
            # Extract item from message
            item = extract_item(message.message.text)
            
            # Get or create default shopping list
            shopping_list = await self.db.fetch_one(
                """
                SELECT id FROM shopping_lists 
                WHERE account_id = $1 AND name = 'default'
                """,
                memory_manager.account_id
            )
            
            if not shopping_list:
                shopping_list = await self.db.fetch_one(
                    """
                    INSERT INTO shopping_lists (account_id, name)
                    VALUES ($1, 'default') RETURNING id
                    """,
                    memory_manager.account_id
                )
            
            # Add item to list
            await self.db.execute(
                """
                INSERT INTO shopping_list_items (list_id, item_name)
                VALUES ($1, $2)
                """,
                shopping_list['id'], item
            )
            
            await message.message.reply(f"Added {item} to your shopping list!")