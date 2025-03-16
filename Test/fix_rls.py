#!/usr/bin/env python3
"""
Fix RLS (Row Level Security) Issues in Supabase

This script enables Row Level Security on all tables in the public schema
and sets up appropriate security policies to ensure data is properly protected.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add the parent directory to the path so we can import modules from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fix_rls")

# Tables that need RLS enabled
TABLES_TO_FIX = [
    "temporary_accounts",
    "account_settings",
    "migration_mapping",
    "email_templates",
    "usage_stats",
    "bot_rules",
    "history_context",
    "ai_model_settings"
]

async def check_rls_status(db):
    """Check the current RLS status of all tables"""
    try:
        if db.supabase is None:
            logger.error("Supabase client is not initialized")
            return
            
        logger.info("Checking current RLS status for tables...")
        
        # SQL to check RLS status
        check_sql = """
        SELECT
            n.nspname as schema,
            c.relname as table,
            CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
        FROM
            pg_class c
        JOIN
            pg_namespace n ON n.oid = c.relnamespace
        WHERE
            n.nspname = 'public'
            AND c.relkind = 'r'
        ORDER BY
            n.nspname, c.relname;
        """
        
        # Execute the SQL
        result = await db.supabase.postgrest.rpc('exec_sql', {'query': check_sql}).execute()
        
        # Process the result
        if result.data and 'result' in result.data:
            tables_data = result.data['result']
            logger.info("Current RLS status:")
            for table_data in tables_data:
                logger.info(f"Table: {table_data['table']}, RLS: {table_data['rls']}")
        else:
            logger.warning("Could not retrieve RLS status")
            
    except Exception as e:
        logger.error(f"Error checking RLS status: {e}")

async def check_existing_policies(db, table_name):
    """Check if policies already exist for a table"""
    try:
        if db.supabase is None:
            logger.error("Supabase client is not initialized")
            return []
            
        # SQL to check existing policies
        check_sql = f"""
        SELECT
            polname as policy_name
        FROM
            pg_policy
        WHERE
            schemaname = 'public'
            AND tablename = '{table_name}';
        """
        
        # Execute the SQL
        result = await db.supabase.postgrest.rpc('exec_sql', {'query': check_sql}).execute()
        
        # Process the result
        if result.data and 'result' in result.data:
            policies = [policy['policy_name'] for policy in result.data['result']]
            logger.info(f"Existing policies for {table_name}: {', '.join(policies) if policies else 'None'}")
            return policies
        else:
            logger.warning(f"Could not retrieve policies for {table_name}")
            return []
            
    except Exception as e:
        logger.error(f"Error checking existing policies for {table_name}: {e}")
        return []

async def enable_rls_for_table(db, table_name):
    """Enable RLS for a specific table and set up appropriate policies"""
    try:
        # Check if Supabase client is available
        if db.supabase is None:
            logger.error("Supabase client is not initialized")
            return False
            
        # Enable RLS on the table
        logger.info(f"Enabling RLS for table: {table_name}")
        
        # SQL to enable RLS
        enable_rls_sql = f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;"
        
        # Execute the SQL
        await db.supabase.postgrest.rpc('exec_sql', {'query': enable_rls_sql}).execute()
        
        # Create policies based on table type
        await create_policies_for_table(db, table_name)
        
        logger.info(f"Successfully enabled RLS for table: {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error enabling RLS for table {table_name}: {e}")
        return False

async def create_policies_for_table(db, table_name):
    """Create appropriate security policies for a table"""
    try:
        # Check existing policies
        existing_policies = await check_existing_policies(db, table_name)
        
        # Define policy name based on table
        if table_name in ["temporary_accounts", "account_settings"]:
            policy_name = "Users can only access their own data"
        elif table_name == "bot_rules":
            policy_name = "Users can only access their own rules"
        elif table_name == "history_context":
            policy_name = "Users can only access their own history"
        elif table_name == "ai_model_settings":
            policy_name = "Users can only access their own settings"
        elif table_name == "usage_stats":
            policy_name = "Users can only access their own usage stats"
        else:
            policy_name = "Enable read access for authenticated users"
        
        # Skip if policy already exists
        if policy_name in existing_policies:
            logger.info(f"Policy '{policy_name}' already exists for table {table_name}, skipping")
            return True
        
        # Different tables need different policies
        if table_name in ["temporary_accounts", "account_settings"]:
            # Users can only see their own accounts
            policy_sql = f"""
            CREATE POLICY "{policy_name}" ON public.{table_name}
            FOR ALL USING (auth.uid() = account_id);
            """
        elif table_name == "bot_rules":
            # Users can only see rules for their accounts
            policy_sql = f"""
            CREATE POLICY "{policy_name}" ON public.{table_name}
            FOR ALL USING (auth.uid() = account_id);
            """
        elif table_name == "history_context":
            # Users can only see history for their accounts
            policy_sql = f"""
            CREATE POLICY "{policy_name}" ON public.{table_name}
            FOR ALL USING (auth.uid() = account_id);
            """
        elif table_name == "ai_model_settings":
            # Users can only see settings for their accounts
            policy_sql = f"""
            CREATE POLICY "{policy_name}" ON public.{table_name}
            FOR ALL USING (auth.uid() = account_id);
            """
        elif table_name == "usage_stats":
            # Users can only see usage stats for their accounts
            policy_sql = f"""
            CREATE POLICY "{policy_name}" ON public.{table_name}
            FOR ALL USING (auth.uid() = account_id);
            """
        else:
            # Generic policy for other tables
            policy_sql = f"""
            CREATE POLICY "{policy_name}" ON public.{table_name}
            FOR SELECT USING (auth.role() = 'authenticated');
            """
        
        # Execute the policy SQL
        await db.supabase.postgrest.rpc('exec_sql', {'query': policy_sql}).execute()
        
        logger.info(f"Created security policy '{policy_name}' for table: {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating policy for table {table_name}: {e}")
        return False

async def main():
    """Main function to fix RLS issues"""
    logger.info("Starting RLS fix process")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize database
    db = Database()
    
    # Check if Supabase is available
    if db.supabase is None:
        logger.error("Supabase client is not initialized. Make sure your environment variables are set correctly.")
        return
    
    # Check current RLS status
    await check_rls_status(db)
    
    # Fix RLS for each table
    for table in TABLES_TO_FIX:
        await enable_rls_for_table(db, table)
    
    # Check RLS status after fixes
    logger.info("Checking RLS status after fixes...")
    await check_rls_status(db)
    
    logger.info("RLS fix process completed")

if __name__ == "__main__":
    asyncio.run(main()) 