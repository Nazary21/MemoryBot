import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug ALL environment variables
all_vars = dict(os.environ)
print("ALL Environment Variables (sanitized):")
for key, value in all_vars.items():
    # Only show first/last 4 chars of sensitive values
    if key in ['TELEGRAM_TOKEN', 'OPENAI_API_KEY']:
        print(f"{key}: {value[:4]}...{value[-4:]}")
    else:
        print(f"{key}: {value}")

# Debug environment
print("All environment variables:", list(os.environ.keys()))
print("TELEGRAM_TOKEN value:", os.getenv("TELEGRAM_TOKEN"))
print("OPENAI_API_KEY value:", os.getenv("OPENAI_API_KEY"))

# Bot Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    print("WARNING: TELEGRAM_TOKEN not found. Available vars:", os.environ)
    raise ValueError("TELEGRAM_TOKEN not found in environment variables")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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