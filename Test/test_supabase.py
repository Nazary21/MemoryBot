#!/usr/bin/env python3
"""
Test Supabase Connection

This script tests the connection to Supabase and performs a simple query.
"""

import logging
from config.database import init_supabase
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_supabase")

def test_supabase_connection():
    """Test the connection to Supabase"""
    logger.info("Initializing Supabase client...")
    client = init_supabase()
    
    if client is None:
        logger.error("Failed to initialize Supabase client")
        return False
    
    logger.info("Supabase client initialized successfully")
    return True

def test_supabase_query():
    """Test a simple query to Supabase"""
    client = init_supabase()
    
    if client is None:
        logger.error("Failed to initialize Supabase client")
        return False
    
    try:
        logger.info("Testing query to chat_history table...")
        result = client.from_('chat_history').select('*').limit(5).execute()
        logger.info(f"Query successful, found {len(result.data)} records")
        
        if len(result.data) > 0:
            logger.info(f"Sample record: {result.data[0]}")
        
        return True
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return False

def test_supabase_tables():
    """List available tables in Supabase"""
    client = init_supabase()
    
    if client is None:
        logger.error("Failed to initialize Supabase client")
        return False
    
    # Try to query specific tables we expect to exist
    tables_to_check = [
        'chat_history',
        'accounts',
        'temporary_accounts',
        'bot_rules',
        'ai_model_settings',
        'history_context'
    ]
    
    logger.info("Checking for specific tables...")
    for table in tables_to_check:
        try:
            logger.info(f"Checking if table '{table}' exists...")
            result = client.from_(table).select('count', count='exact').limit(1).execute()
            logger.info(f"Table '{table}' exists, count: {result.count}")
        except Exception as e:
            logger.warning(f"Table '{table}' check failed: {e}")
    
    return True

def test_insert_message():
    """Test inserting a message into the chat_history table"""
    client = init_supabase()
    
    if client is None:
        logger.error("Failed to initialize Supabase client")
        return False
    
    try:
        logger.info("Testing insert into chat_history table...")
        
        # Create a test message
        test_message = {
            'account_id': 1,
            'telegram_chat_id': 99999,  # Use a test chat ID
            'role': 'user',
            'content': 'This is a test message from test_supabase.py',
            'memory_type': 'short_term',
            'created_at': datetime.now().isoformat()
        }
        
        # Insert the message
        result = client.from_('chat_history').insert(test_message).execute()
        
        if hasattr(result, 'data') and result.data:
            logger.info(f"Insert successful, inserted ID: {result.data[0].get('id', 'unknown')}")
            return True
        else:
            logger.warning("Insert returned no data")
            return False
            
    except Exception as e:
        logger.error(f"Insert failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("Testing Supabase connection...")
    
    if test_supabase_connection():
        logger.info("Connection test passed")
        
        # Test query
        if test_supabase_query():
            logger.info("Query test passed")
        else:
            logger.warning("Query test failed")
        
        # Test listing tables
        if test_supabase_tables():
            logger.info("Table listing test passed")
        else:
            logger.warning("Table listing test failed")
            
        # Test inserting a message
        if test_insert_message():
            logger.info("Insert test passed")
        else:
            logger.warning("Insert test failed")
    else:
        logger.error("Connection test failed")

if __name__ == "__main__":
    main() 