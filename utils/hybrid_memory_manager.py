import logging
import json
import os
from typing import Dict, List, Optional
from utils.memory_manager import MemoryManager
from utils.database import Database

logger = logging.getLogger(__name__)

class HybridMemoryManager:
    VALID_MEMORY_TYPES = {'short_term', 'mid_term', 'whole_history'}
    
    def __init__(self, db: Database):
        self.db = db
        self.file_manager = MemoryManager()  # Original file-based manager
        self.memory_dir = "memory"
        os.makedirs(self.memory_dir, exist_ok=True)
        
    async def get_memory(self, chat_id: int, memory_type: str) -> List[Dict]:
        """Get memory of specific type with fallback to file system"""
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type: {memory_type}")
            
        try:
            # Try database first
            memory = await self.db.get_chat_memory(chat_id, memory_type)
            
            if memory:
                return memory
                
            # Fallback to file system
            file_memory = self._load_memory_from_file(memory_type)
            if file_memory:
                # Migrate to database
                await self._migrate_memory_to_db(chat_id, file_memory, memory_type)
                return await self.db.get_chat_memory(chat_id, memory_type)
                
            return []
            
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return []

    async def add_message(self, chat_id: int, role: str, content: str) -> None:
        """Add a message to all memory types"""
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
            raise

    def _load_memory_from_file(self, memory_type: str) -> List[Dict]:
        """Load memory from file system"""
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
        """Migrate file-based memory to database"""
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
                
            # Record migration
            await self.db.record_migration(chat_id, account['id'])
            
        except Exception as e:
            logger.error(f"Error migrating memory to database: {e}")

    def _get_memory_file(self, memory_type: str) -> str:
        """Get appropriate memory file path"""
        file_map = {
            'short_term': 'short_term.json',
            'mid_term': 'mid_term.json',
            'whole_history': 'whole_history.json'
        }
        return os.path.join(self.memory_dir, file_map.get(memory_type, 'short_term.json')) 