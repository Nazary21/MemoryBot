import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

logger.info(f"SUPABASE_URL is {'set' if SUPABASE_URL else 'NOT SET'}")
logger.info(f"SUPABASE_KEY is {'set' if SUPABASE_KEY else 'NOT SET'}")

def test_supabase_init():
    """Test different methods of initializing Supabase client"""
    try:
        # Method 1: Using create_client
        logger.info("Trying method 1: create_client")
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Method 1 successful!")
            return client
        except Exception as e:
            logger.error(f"Method 1 failed: {e}")
        
        # Method 2: Using Client directly
        logger.info("Trying method 2: Client direct")
        try:
            from supabase import Client
            client = Client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Method 2 successful!")
            return client
        except Exception as e:
            logger.error(f"Method 2 failed: {e}")
            
        # Method 3: Using Client with minimal parameters
        logger.info("Trying method 3: Client with minimal parameters")
        try:
            import supabase
            client = supabase.Client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Method 3 successful!")
            return client
        except Exception as e:
            logger.error(f"Method 3 failed: {e}")
            
        logger.error("All initialization methods failed")
        return None
    except Exception as e:
        logger.error(f"Error in test_supabase_init: {e}")
        return None

if __name__ == "__main__":
    logger.info("Starting Supabase initialization test")
    client = test_supabase_init()
    if client:
        logger.info("Successfully initialized Supabase client")
        try:
            # Test a simple query
            result = client.from_('accounts').select('count', count='exact').limit(1).execute()
            logger.info(f"Query successful: {result}")
        except Exception as e:
            logger.error(f"Query failed: {e}")
    else:
        logger.error("Failed to initialize Supabase client") 