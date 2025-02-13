import os
import json
from config.settings import (
    MEMORY_DIR,
    SHORT_TERM_FILE,
    MID_TERM_FILE,
    WHOLE_HISTORY_FILE,
    HISTORY_CONTEXT_FILE
)

def init_memory_files():
    """Initialize memory directory and files if they don't exist"""
    # Create memory directory
    os.makedirs(MEMORY_DIR, exist_ok=True)
    
    # Initialize files with empty structures
    memory_files = [
        SHORT_TERM_FILE,
        MID_TERM_FILE,
        WHOLE_HISTORY_FILE,
        HISTORY_CONTEXT_FILE
    ]
    
    for file in memory_files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                json.dump([], f)

if __name__ == "__main__":
    init_memory_files() 