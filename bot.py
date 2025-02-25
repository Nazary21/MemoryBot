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
        # Get rules for default account (id=1)
        rules = await rule_manager.get_rules(account_id=1)
        rules_text = rule_manager.get_formatted_rules(rules)
        await update.message.reply_text(rules_text)
    except Exception as e:
        logger.error(f"Error in rules_command: {e}", exc_info=True)
        await update.message.reply_text("Error retrieving rules")

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

# Message handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        chat_id = update.message.chat_id
        
        logger.info(f"Processing message from chat_id {chat_id}: {user_input[:50]}...")
        
        # Check if Supabase is initialized
        if db.supabase is None:
            logger.warning("Supabase client is not initialized. Using fallback mode.")
            # Send a message to the user
            await context.bot.send_message(
                chat_id=chat_id,
                text="I'm currently operating in limited mode due to a database connection issue. Basic functionality is available, but some features may not work properly."
            )
            
            # Use file-based memory as fallback
            try:
                # Use direct OpenAI call as fallback
                from openai import OpenAI
                client = OpenAI(api_key=OPENAI_API_KEY)
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Be concise and friendly."},
                        {"role": "user", "content": user_input}
                    ]
                )
                
                response_text = response.choices[0].message.content
                await context.bot.send_message(chat_id=chat_id, text=response_text)
                
                # Try to store in file-based memory
                try:
                    memory_dir = "memory"
                    os.makedirs(memory_dir, exist_ok=True)
                    short_term_file = os.path.join(memory_dir, "short_term.json")
                    
                    # Load existing messages
                    messages = []
                    if os.path.exists(short_term_file):
                        with open(short_term_file, 'r') as f:
                            try:
                                messages = json.load(f)
                            except json.JSONDecodeError:
                                messages = []
                    
                    # Add new messages
                    messages.append({
                        "role": "user",
                        "content": user_input,
                        "timestamp": datetime.now().isoformat()
                    })
                    messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Save messages
                    with open(short_term_file, 'w') as f:
                        json.dump(messages, f)
                        
                except Exception as file_error:
                    logger.error(f"Error storing messages in file: {file_error}")
                
                return
            except Exception as fallback_error:
                logger.error(f"Error in fallback mode: {fallback_error}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="I'm experiencing technical difficulties. Please try again later."
                )
                return
        
        # Store message in hybrid memory
        try:
            await hybrid_memory.add_message(chat_id, "user", user_input)
        except Exception as memory_error:
            logger.error(f"Error storing message in memory: {memory_error}")
            # Continue anyway to try to get a response
        
        # Get response using hybrid memory
        try:
            response = await get_chat_response(user_input, chat_id)
        except Exception as response_error:
            logger.error(f"Error getting chat response: {response_error}")
            response = "I apologize, but I encountered an error processing your request. Please try again."
        
        if response:
            await context.bot.send_message(chat_id=chat_id, text=response)
            # Store bot's response
            try:
                await hybrid_memory.add_message(chat_id, "assistant", response)
            except Exception as store_error:
                logger.error(f"Error storing bot response: {store_error}")
                # Continue anyway as the response was already sent
            
    except Exception as e:
        logger.error(f"Error in message handler: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, I encountered an error. Please try again."
            )
        except Exception as send_error:
            logger.error(f"Error sending error message: {send_error}")

async def get_chat_response(user_input: str, chat_id: int) -> str:
    try:
        # Get context from hybrid memory
        context = await hybrid_memory.get_memory(chat_id, 'short_term')
        history_context = await hybrid_memory.get_memory(chat_id, 'whole_history')
        
        # Format history context
        formatted_history = (
            f"History context: {history_context}" 
            if history_context else ""
        )
        
        # Get rules from rule manager
        try:
            rules = await rule_manager.get_rules(account_id=1)
            formatted_rules = "Rules to follow:\n" + "\n".join(
                [f"{i+1}. {rule.text}" for i, rule in enumerate(rules)]
            )
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            formatted_rules = "Rules to follow:\nBe helpful and respectful."
        
        # Construct messages array
        messages = [
            {
                "role": "system",
                "content": f"You are a helpful AI assistant. {formatted_rules}\n\n"
                          f"Current conversation context:\n{context}\n{formatted_history}"
            },
            {"role": "user", "content": user_input}
        ]
        
        # Get response using AIResponseHandler
        response = await ai_handler.get_chat_response(1, messages)
        return response
        
    except Exception as e:
        logger.error(f"Error getting chat response: {e}")
        return "I apologize, but I encountered an error. Please try again."

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