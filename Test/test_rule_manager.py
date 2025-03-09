import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import modules from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.rule_manager import RuleManager
from utils.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_rule_manager")

async def test_rule_manager():
    # Initialize database and rule manager
    db = Database()
    rule_manager = RuleManager(db)
    
    # Get rules for account 1
    logger.info("Getting rules for account 1...")
    rules = await rule_manager.get_rules(account_id=1)
    logger.info(f"Found {len(rules)} rules")
    
    # Print each rule
    for i, rule in enumerate(rules):
        logger.info(f"Rule {i+1}: {rule.text} (Priority: {rule.priority}, Category: {rule.category})")
    
    # Get formatted rules
    formatted_rules = rule_manager.get_formatted_rules(rules)
    logger.info(f"Formatted rules:\n{formatted_rules}")

if __name__ == "__main__":
    asyncio.run(test_rule_manager()) 