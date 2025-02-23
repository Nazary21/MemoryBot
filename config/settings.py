import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug environment
print("Environment variables available:", list(os.environ.keys()))

# Bot Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
print("Found TELEGRAM_TOKEN:", bool(TELEGRAM_TOKEN))
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in environment variables")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("Found OPENAI_API_KEY:", bool(OPENAI_API_KEY))
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Memory Configuration
SESSION_DURATION = 6 * 3600  # 6 hours (default)
MID_TERM_MESSAGE_LIMIT = 200

# File Paths
MEMORY_DIR = "memory"
SHORT_TERM_FILE = os.path.join(MEMORY_DIR, "short_term.json")
MID_TERM_FILE = os.path.join(MEMORY_DIR, "mid_term.json")
WHOLE_HISTORY_FILE = os.path.join(MEMORY_DIR, "whole_history.json")
HISTORY_CONTEXT_FILE = os.path.join(MEMORY_DIR, "history_context.json") 