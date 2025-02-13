import json
import time
import os
from typing import List, Dict, Any
from config.settings import (
    SHORT_TERM_FILE,
    MID_TERM_FILE,
    WHOLE_HISTORY_FILE,
    HISTORY_CONTEXT_FILE,
    SESSION_DURATION,
    MID_TERM_MESSAGE_LIMIT,
    MEMORY_DIR
)

class MemoryManager:
    def __init__(self):
        # Ensure memory directory exists
        os.makedirs(MEMORY_DIR, exist_ok=True)
        
    def _load_memory(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _save_memory(self, file_path: str, data: List[Dict[str, Any]]) -> None:
        with open(file_path, "w") as f:
            json.dump(data, ensure_ascii=False, indent=4, fp=f)

    def update_memory(self, user_input: str, assistant_response: str) -> None:
        current_time = time.time()
        message_pair = [
            {"role": "user", "content": user_input, "timestamp": current_time},
            {"role": "assistant", "content": assistant_response, "timestamp": current_time}
        ]

        # Update whole history
        whole_history = self._load_memory(WHOLE_HISTORY_FILE)
        whole_history.extend(message_pair)
        self._save_memory(WHOLE_HISTORY_FILE, whole_history)

        # Update short-term memory
        short_term = self._load_memory(SHORT_TERM_FILE)
        short_term.extend(message_pair)
        
        # Filter out old messages from short-term
        current_time = time.time()
        short_term = [
            msg for msg in short_term 
            if current_time - msg["timestamp"] <= SESSION_DURATION
        ]
        self._save_memory(SHORT_TERM_FILE, short_term)

        # Move old messages to mid-term
        mid_term = self._load_memory(MID_TERM_FILE)
        moved_to_mid = [
            msg for msg in short_term 
            if current_time - msg["timestamp"] > SESSION_DURATION
        ]
        
        if moved_to_mid:
            mid_term.extend(moved_to_mid)
            # Keep only the last MID_TERM_MESSAGE_LIMIT messages
            mid_term = mid_term[-MID_TERM_MESSAGE_LIMIT:]
            self._save_memory(MID_TERM_FILE, mid_term)

    def get_context(self) -> List[Dict[str, str]]:
        short_term = self._load_memory(SHORT_TERM_FILE)
        history_context = self._load_memory(HISTORY_CONTEXT_FILE)
        
        # Convert timestamps to readable format for the context
        formatted_short_term = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in short_term
        ]
        
        return formatted_short_term, history_context 