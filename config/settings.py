import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Memory Configuration
SESSION_DURATION = 6 * 3600  # 6 hours (default)
MID_TERM_MESSAGE_LIMIT = 200

# File Paths
MEMORY_DIR = "memory"
SHORT_TERM_FILE = os.path.join(MEMORY_DIR, "short_term.json")
MID_TERM_FILE = os.path.join(MEMORY_DIR, "mid_term.json")
WHOLE_HISTORY_FILE = os.path.join(MEMORY_DIR, "whole_history.json")
HISTORY_CONTEXT_FILE = os.path.join(MEMORY_DIR, "history_context.json") 