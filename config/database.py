import os
from dotenv import load_dotenv
import logging
import importlib.metadata

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

def init_supabase():
    """Initialize Supabase client"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            return None
            
        logger.info(f"Initializing Supabase client with URL: {SUPABASE_URL[:10]}...")
        
        # Check if supabase package is installed
        try:
            supabase_version = importlib.metadata.version('supabase')
            logger.info(f"Detected supabase version: {supabase_version}")
        except importlib.metadata.PackageNotFoundError:
            logger.error("Supabase package is not installed. Please install it with: pip install supabase>=2.3.0")
            return None
        
        # Initialize Supabase client using the modern approach
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully with create_client")
            
            # Test connection
            try:
                # Modern API uses .from_() instead of .table()
                test_result = client.from_('accounts').select('count', count='exact').limit(1).execute()
                logger.info("Supabase connection test successful")
            except Exception as test_error:
                logger.warning(f"Supabase connection test failed: {test_error}")
                # Continue anyway as the table might not exist yet
                
            return client
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}")
            return None
    except Exception as e:
        logger.error(f"Error initializing Supabase: {e}")
        return None