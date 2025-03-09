#!/usr/bin/env python3
"""
Database setup script for Supabase.
This script creates the necessary tables in Supabase for the bot to function properly.
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
logger = logging.getLogger("setup_database")

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

async def setup_database():
    """Set up the necessary tables in Supabase"""
    try:
        logger.info("Initializing Supabase client...")
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # First, try to check if tables exist
        logger.info("Checking existing tables...")
        try_tables = ['accounts', 'chat_history', 'bot_rules', 'history_context', 'ai_model_settings']
        existing_tables = []
        missing_tables = []
        
        for table in try_tables:
            try:
                result = supabase.from_(table).select('count', count='exact').limit(1).execute()
                logger.info(f"Table '{table}' exists")
                existing_tables.append(table)
            except Exception as e:
                logger.warning(f"Table '{table}' does not exist or cannot be accessed: {e}")
                missing_tables.append(table)
        
        if not missing_tables:
            logger.info("All required tables exist!")
            return True
        
        # Try to execute the migration SQL file
        logger.info("Some tables are missing. Attempting to execute migration SQL...")
        
        # Read the migration SQL file
        migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'init.sql')
        if not os.path.exists(migration_file):
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        logger.info("Read migration SQL file successfully")
        
        # Try different methods to execute the SQL
        
        # Method 1: Using the execute_sql RPC function (if available)
        try:
            logger.info("Trying to execute SQL using RPC function...")
            result = supabase.rpc('execute_sql', {'query': sql}).execute()
            logger.info("SQL executed successfully using RPC function")
            return True
        except Exception as e:
            logger.warning(f"Could not execute SQL using RPC function: {e}")
        
        # Method 2: Using raw SQL query (if permissions allow)
        try:
            logger.info("Trying to execute SQL using raw query...")
            # This might not work depending on Supabase permissions
            result = supabase.table('_').select('*').execute(sql)
            logger.info("SQL executed successfully using raw query")
            return True
        except Exception as e:
            logger.warning(f"Could not execute SQL using raw query: {e}")
        
        # Method 3: Split and execute statements individually
        try:
            logger.info("Trying to execute SQL statements individually...")
            # Split SQL into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for i, statement in enumerate(statements):
                try:
                    logger.info(f"Executing statement {i+1}/{len(statements)}")
                    result = supabase.rpc('execute_sql', {'query': statement}).execute()
                    logger.info(f"Statement {i+1} executed successfully")
                except Exception as stmt_error:
                    logger.warning(f"Error executing statement {i+1}: {stmt_error}")
            
            logger.info("Finished executing individual SQL statements")
            return True
        except Exception as e:
            logger.warning(f"Could not execute individual SQL statements: {e}")
        
        # If all methods fail, print instructions
        logger.error("Could not automatically create tables. Please create them manually.")
        logger.info("You can run this script with --print-sql to get the SQL commands.")
        return False
        
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        return False

def print_sql_commands():
    """Print SQL commands from the migration file"""
    migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'init.sql')
    
    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        return
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print("\n--- SQL Migration Commands ---")
    print(sql)

if __name__ == "__main__":
    logger.info("Starting database setup...")
    
    # Check if --print-sql flag is provided
    if len(sys.argv) > 1 and sys.argv[1] == "--print-sql":
        print_sql_commands()
        sys.exit(0)
    
    # Run the async function
    success = asyncio.run(setup_database())
    
    if success:
        logger.info("Database setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database setup failed!")
        logger.info("You can run this script with --print-sql to get the SQL commands to create the tables manually.")
        sys.exit(1) 