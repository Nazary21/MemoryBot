import logging
import json
import os
from typing import Dict, List, Optional, Any
from utils.memory_manager import MemoryManager
from utils.database import Database

HISTORY_CONTEXT_FILE = "history_context.json"

logger = logging.getLogger(__name__)

class HybridMemoryManager:
    """
    A hybrid memory management system that combines database and file-based storage.
    
    This class provides a robust memory system that:
    1. Primarily uses a database (Supabase) for storage
    2. Automatically falls back to file-based storage when database is unavailable
    3. Supports multiple memory types: short_term, mid_term, and whole_history
    4. Handles data migration between storage systems
    
    The fallback mechanism ensures the bot continues to function even when:
    - Database connection is lost
    - Database operations fail
    - System is running in limited connectivity mode
    
    Memory Types:
    - short_term: Recent messages (last 50)
    - mid_term: Extended conversation context (last 200)
    - whole_history: Complete conversation archive
    """
    
    VALID_MEMORY_TYPES = {'short_term', 'mid_term', 'whole_history'}
    
    def __init__(self, db: Database, account_id: int = None):
        """
        Initialize the hybrid memory manager.
        
        Args:
            db: Database instance for primary storage
            account_id: Optional account ID for file storage (defaults to 1 for system-level fallback)
            
        The manager sets up both database and file-based storage systems:
        1. Database connection through the provided Database instance
        2. File-based backup system in account-specific directories
        3. Legacy file manager for backward compatibility
        """
        self.db = db
        # Use provided account_id or default to 1 for system-level fallback
        self.account_id = account_id if account_id is not None else 1
        # Initialize file manager with the correct account
        self.file_manager = MemoryManager(account_id=self.account_id, db=db)
        # Base memory directory
        self.memory_dir = "memory"
        os.makedirs(self.memory_dir, exist_ok=True)
        
    async def get_memory(self, chat_id: int, memory_type: str) -> List[Dict]:
        """
        Retrieve memory of a specific type with automatic fallback.
        
        The retrieval process follows this sequence:
        1. Validate memory type
        2. Try to fetch from database
        3. If database fails, check file system
        4. If file data exists, attempt to migrate it to database
        5. Return empty list if all attempts fail
        
        Args:
            chat_id: The chat ID to get memory for
            memory_type: Type of memory to retrieve (short_term/mid_term/whole_history)
            
        Returns:
            List of message dictionaries
        """
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type: {memory_type}")
            
        try:
            # Try database first - pass None as limit to get all messages
            memory = await self.db.get_chat_memory(chat_id, memory_type, limit=None)
            
            if memory:
                return memory
                
            # Fallback to file system
            file_memory = self._load_memory_from_file(memory_type)
            if file_memory:
                # Migrate to database if possible
                await self._migrate_memory_to_db(chat_id, file_memory, memory_type)
                return await self.db.get_chat_memory(chat_id, memory_type, limit=None)
                
            return []
            
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return []

    async def add_message(self, chat_id: int, role: str, content: str) -> None:
        """
        Add a message to all memory types with fallback handling.
        
        The message is stored in:
        1. whole_history (complete archive)
        2. short_term (recent context)
        3. mid_term (if short_term exceeds threshold)
        
        If database storage fails, messages are saved to files.
        
        Args:
            chat_id: The chat ID to store the message for
            role: Message role (user/assistant/system)
            content: The message content
        """
        try:
            account = await self.db.get_or_create_temporary_account(chat_id)
            
            # Always add to whole_history
            await self.db.store_chat_message(
                account_id=account['id'],
                chat_id=chat_id,
                role=role,
                content=content,
                memory_type='whole_history'
            )
            
            # Add to short_term
            await self.db.store_chat_message(
                account_id=account['id'],
                chat_id=chat_id,
                role=role,
                content=content,
                memory_type='short_term'
            )
            
            # Add to mid_term if short_term gets too large
            short_term = await self.db.get_chat_memory(chat_id, 'short_term')
            if len(short_term) > 50:  # Configurable threshold
                await self.db.store_chat_message(
                    account_id=account['id'],
                    chat_id=chat_id,
                    role=role,
                    content=content,
                    memory_type='mid_term'
                )
        
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            # Fallback to file-based storage
            try:
                self.file_manager.add_message(role, content)
            except Exception as file_error:
                logger.error(f"File fallback also failed: {file_error}")
            raise

    def _load_memory_from_file(self, memory_type: str) -> List[Dict]:
        """
        Load memory from file system (fallback storage).
        
        Args:
            memory_type: Type of memory to load
            
        Returns:
            List of messages from file storage
        """
        try:
            file_path = self._get_memory_file(memory_type)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading memory from file: {e}")
            return []

    async def _migrate_memory_to_db(self, chat_id: int, memory: List[Dict], memory_type: str):
        """
        Migrate file-based memory to database storage.
        
        This process:
        1. Creates/gets temporary account
        2. Transfers messages to database
        3. Records the migration
        
        Args:
            chat_id: The chat ID to migrate memory for
            memory: List of messages to migrate
            memory_type: Type of memory being migrated
        """
        try:
            account = await self.db.get_or_create_temporary_account(chat_id)
            
            for msg in memory:
                await self.db.store_chat_message(
                    account_id=account['id'],
                    chat_id=chat_id,
                    role=msg.get('role', 'user'),
                    content=msg.get('content', ''),
                    memory_type=memory_type
                )
                
            # Record successful migration
            await self.db.record_migration(chat_id, account['id'])
            
        except Exception as e:
            logger.error(f"Error migrating memory to database: {e}")

    def _get_memory_file(self, memory_type: str, account_id: int = 1) -> str:
        """
        Get the appropriate file path for a memory type.
        
        Args:
            memory_type: Type of memory to get path for
            account_id: Account ID for account-specific storage
            
        Returns:
            Path to the memory file
        """
        file_map = {
            'short_term': 'short_term.json',
            'mid_term': 'mid_term.json',
            'whole_history': 'whole_history.json'
        }
        
        # Use account-specific directory
        account_dir = os.path.join(self.memory_dir, f"account_{account_id}")
        os.makedirs(account_dir, exist_ok=True)
        
        return os.path.join(account_dir, file_map.get(memory_type, 'short_term.json'))

    def get_history_context(self) -> str:
        """
        Get historical context summary using direct file access.
        
        Returns:
            String containing the formatted history context
        """
        try:
            history_file = os.path.join(self.memory_dir, f"account_{self.account_id}", HISTORY_CONTEXT_FILE)
            
            if not os.path.exists(history_file):
                logger.info(f"No history context file found for account {self.account_id}")
                return ""
                
            with open(history_file, 'r') as f:
                context_data = json.load(f)
                
            if not context_data:
                logger.info("History context file is empty")
                return ""
                
            # Handle both array and single entry formats
            if isinstance(context_data, list):
                if len(context_data) == 0:
                    return ""
                latest_context = context_data[0]
                return latest_context.get('summary', '')
            elif isinstance(context_data, dict):
                return context_data.get('summary', '')
            else:
                logger.warning("Invalid history context format")
                return ""
                
        except Exception as e:
            logger.error(f"Error getting history context: {e}")
            return "" 