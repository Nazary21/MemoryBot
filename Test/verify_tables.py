#!/usr/bin/env python3
"""
Script to verify if all required tables exist in Supabase.
Run this script after executing the SQL commands in the Supabase SQL editor.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("verify_tables")

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def verify_tables():
    """Verify if all required tables exist in Supabase"""
    try:
        logger.info("Initializing Supabase client...")
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Check which tables exist
        logger.info("Checking tables...")
        required_tables = [
            'accounts', 
            'chat_history', 
            'bot_rules', 
            'history_context', 
            'ai_model_settings', 
            'temporary_accounts', 
            'account_chats', 
            'account_settings', 
            'migration_mapping', 
            'usage_stats'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in required_tables:
            try:
                result = supabase.from_(table).select('count', count='exact').limit(1).execute()
                logger.info(f"✅ Table '{table}' exists")
                existing_tables.append(table)
            except Exception as e:
                logger.error(f"❌ Table '{table}' does not exist or cannot be accessed: {e}")
                missing_tables.append(table)
        
        # Print summary
        print("\n=== TABLE VERIFICATION SUMMARY ===")
        print(f"Total required tables: {len(required_tables)}")
        print(f"Existing tables: {len(existing_tables)} / {len(required_tables)}")
        
        if missing_tables:
            print(f"\n❌ Missing tables ({len(missing_tables)}):")
            for table in missing_tables:
                print(f"  - {table}")
            print("\nPlease create the missing tables using the SQL commands from create_missing_tables.py")
            return False
        else:
            print("\n✅ All required tables exist!")
            print("\nYour Supabase database is properly set up. The HybridMemoryManager should now work correctly.")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying tables: {e}")
        return False

async def main():
    """Main function"""
    success = await verify_tables()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 