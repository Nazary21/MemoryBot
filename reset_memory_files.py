#!/usr/bin/env python3
"""
Reset Memory Files

This script resets memory files that have grown too large.
It preserves the most recent messages up to the specified limit.
"""

import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reset_memory")

# Constants
MEMORY_DIR = "memory"
ACCOUNT_DIRS = ["account_0", "account_1"]  # Add more if needed
MEMORY_TYPES = {
    "short_term.json": 50,  # Limit to 50 messages
    "mid_term.json": 200,   # Limit to 200 messages
    "whole_history.json": 1000  # Limit to 1000 messages
}

def reset_memory_file(file_path, max_messages):
    """Reset a memory file to contain only the most recent messages up to the limit"""
    try:
        # Check if file exists and has content
        if not os.path.exists(file_path):
            logger.info(f"File {file_path} does not exist, creating empty array")
            with open(file_path, 'w') as f:
                json.dump([], f)
            return True
        
        # Check file size
        file_size = os.path.getsize(file_path)
        logger.info(f"File {file_path} size: {file_size / (1024 * 1024):.2f} MB")
        
        # Read file content
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    logger.info(f"File {file_path} is empty, initializing as empty array")
                    with open(file_path, 'w') as f:
                        json.dump([], f)
                    return True
                
                # Parse JSON
                try:
                    data = json.loads(content)
                    
                    # Handle different formats
                    if isinstance(data, list):
                        messages = data
                    elif isinstance(data, dict) and not data:
                        messages = []
                    else:
                        logger.warning(f"Unexpected data format in {file_path}, initializing as empty array")
                        messages = []
                    
                    # Limit messages to max_messages
                    if len(messages) > max_messages:
                        logger.info(f"Limiting {file_path} from {len(messages)} to {max_messages} messages")
                        messages = messages[-max_messages:]
                    
                    # Write back to file
                    with open(file_path, 'w') as f:
                        json.dump(messages, f)
                    
                    logger.info(f"Successfully reset {file_path} to {len(messages)} messages")
                    return True
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in {file_path}, initializing as empty array")
                    with open(file_path, 'w') as f:
                        json.dump([], f)
                    return True
                    
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            # If we can't read the file, create a new empty one
            with open(file_path, 'w') as f:
                json.dump([], f)
            logger.info(f"Created new empty file for {file_path}")
            return True
            
    except Exception as e:
        logger.error(f"Error resetting {file_path}: {e}")
        return False

def main():
    """Main function to reset all memory files"""
    logger.info("Starting memory file reset")
    
    # Process each account directory
    for account_dir in ACCOUNT_DIRS:
        account_path = os.path.join(MEMORY_DIR, account_dir)
        
        # Skip if directory doesn't exist
        if not os.path.exists(account_path):
            logger.info(f"Directory {account_path} does not exist, skipping")
            continue
        
        logger.info(f"Processing directory: {account_path}")
        
        # Process each memory type
        for memory_type, max_messages in MEMORY_TYPES.items():
            file_path = os.path.join(account_path, memory_type)
            reset_memory_file(file_path, max_messages)
    
    logger.info("Memory file reset completed")

if __name__ == "__main__":
    main() 