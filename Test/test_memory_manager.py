import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import modules from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.hybrid_memory_manager import HybridMemoryManager
from utils.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_memory_manager")

async def test_memory_manager():
    # Initialize database and memory manager
    db = Database()
    memory_manager = HybridMemoryManager(db, account_id=1)
    
    # Test chat ID
    test_chat_id = 12345
    
    # Add a test message
    logger.info(f"Adding test message to chat {test_chat_id}...")
    await memory_manager.add_message(test_chat_id, "user", "This is a test message")
    logger.info("Test message added")
    
    # Get short-term memory
    logger.info(f"Getting short-term memory for chat {test_chat_id}...")
    short_term = await memory_manager.get_memory(test_chat_id, 'short_term')
    logger.info(f"Retrieved {len(short_term)} messages from short-term memory")
    
    # Print each message
    for i, msg in enumerate(short_term):
        logger.info(f"Message {i+1}: {msg.get('role')}: {msg.get('content')}")
    
    # Get history context
    logger.info("Getting history context...")
    history_context = memory_manager.get_history_context()
    logger.info(f"History context: {history_context}")

if __name__ == "__main__":
    asyncio.run(test_memory_manager()) 