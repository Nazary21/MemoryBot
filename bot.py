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
    try:
        # Get context from memory
        short_term, history_context = memory_manager.get_context()
        
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
            return f"Mock response to: {user_input}"
            
        # Get response from OpenAI
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        assistant_response = response.choices[0].message.content
        
        # Store messages as proper format
        memory_manager.update_memory(
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": assistant_response}
        )
        
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

# Add this near your other FastAPI routes
@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Bot is running"}

# Webhook handler
@app.post("/{token:path}")
async def telegram_webhook(token: str, request: Request):
    try:
        # Verify token
        if token != TELEGRAM_TOKEN:
            logger.error(f"Invalid token: {token}")
            return {"error": "Invalid token"}
            
        body = await request.json()
        logger.info(f"Received webhook with body: {body}")
        
        # Create update object with bot instance
        update = Update.de_json(body, application.bot)
        logger.info(f"Created update object: {update}")
        
        if update.message and update.message.text:
            # Handle commands
            if update.message.text.startswith('/'):
                logger.info(f"Processing command: {update.message.text}")
                await application.process_update(update)
                return {"status": "command processed"}
                
            # Handle regular messages
            logger.info(f"Processing message: {update.message.text}")
            try:
                response = await get_chat_response(update.message.text)
                logger.info(f"Got response: {response}")
                
                sent_message = await application.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=response
                )
                logger.info(f"Sent message: {sent_message}")
                return {"status": "ok"}
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await application.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="I apologize, but I encountered an error. Please try again."
                )
                return {"error": "Message processing failed"}
                
        return {"status": "no message"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"error": str(e)}

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
        "/analyze - Analyze conversation history\n"
        "/context - Show historical context\n"
        "/midterm - Show mid-term memory stats\n"
        "/shortterm - Show short-term memory stats\n"
        "/wholehistory - Show whole history stats\n"
        "/historycontext - Show full history context"
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

# Add these new command handlers after other command handlers

async def mid_term_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mid-term memory stats"""
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
        logger.error(f"Error in mid_term_history_command: {e}")
        await update.message.reply_text("Error retrieving mid-term history stats")

async def short_term_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show short-term memory stats"""
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
        logger.error(f"Error in short_term_history_command: {e}")
        await update.message.reply_text("Error retrieving short-term history stats")

async def whole_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show whole history stats"""
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
        logger.error(f"Error in whole_history_command: {e}")
        await update.message.reply_text("Error retrieving whole history stats")

async def history_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full history context"""
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
            
        # Telegram message limit is 4096 characters
        if len(response) > 4000:
            response = response[:3997] + "..."
            
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in history_context_command: {e}")
        await update.message.reply_text("Error retrieving history context")

# Update the application initialization section
async def setup_commands():
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

# Update the main section
if __name__ == "__main__":
    import uvicorn
    import asyncio
    
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
        application.add_handler(CommandHandler("midterm", mid_term_history_command))
        application.add_handler(CommandHandler("shortterm", short_term_history_command))
        application.add_handler(CommandHandler("wholehistory", whole_history_command))
        application.add_handler(CommandHandler("historycontext", history_context_command))
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