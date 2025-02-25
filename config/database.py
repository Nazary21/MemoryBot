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
        
        # Check Supabase package version
        try:
            import supabase
            logger.info(f"Using Supabase package version: {supabase.__version__}")
        except (ImportError, AttributeError):
            logger.warning("Could not determine Supabase package version")
        
        # Create client with only required parameters
        # This ensures compatibility with different versions of the Supabase client
        try:
            # First try the simplest approach with just URL and key
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except TypeError as type_error:
            if "proxy" in str(type_error):
                logger.warning(f"TypeError with proxy parameter: {type_error}")
                # Try importing directly from client module for more control
                from supabase.client import Client as SupabaseClient
                client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
            else:
                # Re-raise if it's a different TypeError
                raise
        
        # Test the connection
        try:
            # Simple query to test connection
            test_result = client.table('accounts').select('count(*)', count='exact').limit(1).execute()
            logger.info(f"Supabase connection test successful")
        except Exception as test_error:
            logger.warning(f"Supabase connection test failed: {test_error}")
            # Try an alternative test query
            try:
                # Try a raw SQL query as a fallback
                test_result = client.rpc('execute_sql', {'query': 'SELECT 1 as test'}).execute()
                logger.info("Alternative connection test successful")
            except Exception as alt_test_error:
                logger.warning(f"Alternative connection test also failed: {alt_test_error}")
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
            # Try importing directly from client module
            from supabase.client import Client as SupabaseClient
            # Try with minimal parameters
            client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Alternative initialization successful")
            return client
        except Exception as alt_error:
            logger.error(f"Alternative initialization also failed: {alt_error}")
            
            # Try one more approach with direct HTTP client
            try:
                logger.info("Trying HTTP client approach...")
                import httpx
                from supabase.client import SupabaseClient
                # Create HTTP client manually
                http_client = httpx.Client()
                client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY, http_client=http_client)
                logger.info("HTTP client approach successful")
                return client
            except Exception as http_error:
                logger.error(f"HTTP client approach failed: {http_error}")
        
        # Return None instead of raising to allow the application to continue
        # with limited functionality rather than crashing
        return None