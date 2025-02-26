import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Setup logging
logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, account_id: int, db):
        self.account_id = account_id
        self.db = db
        
        # Ensure memory directory exists
        self.memory_dir = f"memory/account_{account_id}"
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Initialize file paths
        self.short_term_file = os.path.join(self.memory_dir, "short_term.json")
        self.mid_term_file = os.path.join(self.memory_dir, "mid_term.json")
        self.whole_history_file = os.path.join(self.memory_dir, "whole_history.json")
        self.history_file = os.path.join(self.memory_dir, "history_context.json")
        
        # Ensure all memory files exist
        self._ensure_memory_files()

    def update_memory(self, user_message: Dict, assistant_message: Dict) -> None:
        """Update all memory levels with new messages"""
        try:
            # Add timestamp if not present
            timestamp = datetime.now().isoformat()
            if isinstance(user_message, dict) and "timestamp" not in user_message:
                user_message["timestamp"] = timestamp
            if isinstance(assistant_message, dict) and "timestamp" not in assistant_message:
                assistant_message["timestamp"] = timestamp

            # Update short-term memory
            short_term = self._load_memory(self.short_term_file)
            short_term.extend([user_message, assistant_message])
            self._save_memory(self.short_term_file, short_term[-50:])  # Keep last 50 messages

            # Update mid-term memory
            mid_term = self._load_memory(self.mid_term_file)
            mid_term.extend([user_message, assistant_message])
            self._save_memory(self.mid_term_file, mid_term[-200:])  # Keep last 200 messages

            # Update whole history
            whole_history = self._load_memory(self.whole_history_file)
            whole_history.extend([user_message, assistant_message])
            self._save_memory(self.whole_history_file, whole_history)

        except Exception as e:
            logger.error(f"Error updating memory: {e}", exc_info=True)
            raise

    def get_context(self) -> str:
        """Get current context from memory"""
        try:
            short_term = self._load_memory(self.short_term_file)
            return "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in short_term[-10:]])
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return ""

    def get_history_context(self) -> str:
        """Get historical context summary"""
        try:
            history_context = self._load_memory(self.history_file)
            
            # Initialize history context if empty
            if not history_context:
                logger.info(f"Initializing history context for account {self.account_id}")
                # Add initial context entry
                initial_context = {
                    "timestamp": datetime.now().isoformat(),
                    "category": "system",
                    "summary": "Chat history initialized."
                }
                history_context = [initial_context]
                self._save_memory(self.history_file, history_context)
            
            # Format context entries with timestamps
            formatted_entries = []
            for entry in history_context:
                timestamp = entry.get("timestamp", "")
                summary = entry.get("summary", "")
                category = entry.get("category", "general")
                if timestamp and summary:
                    formatted_entries.append(f"[{timestamp}] ({category}) {summary}")
                else:
                    formatted_entries.append(summary)
            
            return "\n".join(formatted_entries) if formatted_entries else "No history available yet."
        except Exception as e:
            logger.error(f"Error getting history context for account {self.account_id}: {e}")
            return "Error retrieving history context."

    def _load_memory(self, file_path: str) -> list:
        """Load memory from file with error handling"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading memory file {file_path}: {e}")
            return []

    def _save_memory(self, file_path: str, data: list) -> None:
        """Save memory to file with error handling"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory file {file_path}: {e}")
            raise

    def add_message(self, role: str, content: str) -> None:
        """Add a new message to short term memory"""
        try:
            messages = self._load_memory(self.short_term_file)
            
            messages.append({
                "timestamp": datetime.now().isoformat(),
                "role": role,
                "content": content
            })
            
            # Keep only last 50 messages
            messages = messages[-50:]
            self._save_memory(self.short_term_file, messages)
        except Exception as e:
            logger.error(f"Error adding message to memory: {e}")

    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Get recent messages from short term memory"""
        try:
            messages = self._load_memory(self.short_term_file)
            return messages[-limit:]
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []

    def add_context(self, context: str, category: str = "general") -> None:
        """Add a new context entry to history"""
        try:
            history = self._load_memory(self.history_file)
            
            # Initialize if empty
            if not history:
                history = []
            
            history.append({
                "timestamp": datetime.now().isoformat(),
                "category": category,
                "summary": context
            })
            
            # Keep only last 100 entries to prevent unlimited growth
            history = history[-100:]
            
            self._save_memory(self.history_file, history)
            logger.info(f"Added new context entry for account {self.account_id}: {context[:50]}...")
        except Exception as e:
            logger.error(f"Error adding context to history: {e}")

    def clear_short_term(self) -> None:
        """Clear short term memory"""
        with open(self.short_term_file, 'w') as f:
            json.dump([], f)

    def clear_history(self) -> None:
        """Clear historical context"""
        with open(self.history_file, 'w') as f:
            json.dump([], f)

    async def add_to_memory(self, message):
        await self.db.execute(
            """
            INSERT INTO chat_history (account_id, message) 
            VALUES ($1, $2)
            """,
            self.account_id, message
        ) 

    def _ensure_memory_files(self) -> None:
        """Ensure all memory files exist with proper structure"""
        try:
            for file_path in [self.short_term_file, self.mid_term_file, 
                            self.whole_history_file, self.history_file]:
                if not os.path.exists(file_path):
                    self._save_memory(file_path, [])
                    logger.info(f"Created memory file: {file_path}")
        except Exception as e:
            logger.error(f"Error ensuring memory files: {e}") 