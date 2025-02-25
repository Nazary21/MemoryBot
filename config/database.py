import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Configure logging specifically for this module
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Log credential status (without revealing actual values)
logger.info(f"SUPABASE_URL is {'set' if SUPABASE_URL else 'NOT SET'}")
logger.info(f"SUPABASE_KEY is {'set' if SUPABASE_KEY else 'NOT SET'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

def init_supabase():
    """Initialize Supabase client"""
    try:
        logger.info(f"Initializing Supabase client with URL: {SUPABASE_URL[:10]}...")
        
        # Create client with only positional arguments, no keyword args
        # This ensures compatibility with supabase==2.3.1
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test the connection
        try:
            # Simple query to test connection
            test_result = client.table('accounts').select('count(*)', count='exact').limit(1).execute()
            logger.info(f"Supabase connection test successful: {test_result}")
        except Exception as test_error:
            logger.warning(f"Supabase connection test failed: {test_error}")
            # Continue anyway as this is just a test
        
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Error initializing Supabase: {e}")
        # Log more details about the error for debugging
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        
        # Try with a different approach as fallback
        try:
            logger.info("Trying alternative initialization method...")
            from supabase.client import Client as SupabaseClient
            client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Alternative initialization successful")
            return client
        except Exception as alt_error:
            logger.error(f"Alternative initialization also failed: {alt_error}")
        
        # Return None instead of raising to allow the application to continue
        # with limited functionality rather than crashing
        return None