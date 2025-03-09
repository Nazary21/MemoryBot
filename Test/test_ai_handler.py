import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import modules from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai_response import AIResponseHandler
from utils.database import Database
from utils.rule_manager import RuleManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_ai_handler")

async def test_ai_handler():
    # Initialize database, rule manager, and AI handler
    db = Database()
    rule_manager = RuleManager(db)
    ai_handler = AIResponseHandler(db)
    
    # Get account model settings
    logger.info("Getting account model settings...")
    settings = await ai_handler.get_account_model_settings(account_id=1)
    logger.info(f"Account model settings: {settings}")
    
    # Get rules
    logger.info("Getting rules...")
    rules = await rule_manager.get_rules(account_id=1)
    rules_text = rule_manager.get_formatted_rules(rules)
    logger.info(f"Rules:\n{rules_text}")
    
    # Prepare messages
    system_message = f"You are a helpful assistant. Follow these rules:\n{rules_text}"
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": "Hello, how are you today?"}
    ]
    
    # Get AI response
    logger.info("Getting AI response...")
    try:
        response = await ai_handler.get_chat_response(account_id=1, messages=messages)
        logger.info(f"AI response: {response}")
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_handler()) 