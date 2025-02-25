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
            logger.error("Supabase package is not installed. Please install it with: pip install supabase==2.8.1")
            return None
        
        # Initialize Supabase client using the modern approach
        try:
            from supabase import create_client
            
            # Create client with only the required parameters to avoid compatibility issues
            # The 'proxy' parameter was causing issues in version 2.8.1
            client = create_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY
            )
            
            logger.info("Supabase client initialized successfully with create_client")
            
            # Test connection
            try:
                # Modern API uses .from_() instead of .table()
                test_result = client.from_('accounts').select('count', count='exact').limit(1).execute()
                logger.info(f"Supabase connection test successful: {test_result.count if hasattr(test_result, 'count') else 'unknown'} accounts found")
            except Exception as test_error:
                logger.warning(f"Supabase connection test failed: {test_error}")
                # Continue anyway as the table might not exist yet
                
            return client
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}")
            
            # Try alternative initialization method if the first one fails
            try:
                logger.info("Trying alternative initialization method...")
                import supabase
                
                # Check if we're using a version that requires different initialization
                if supabase_version.startswith('2.8'):
                    logger.info("Using initialization method for version 2.8+")
                    client = supabase.Client(SUPABASE_URL, SUPABASE_KEY)
                    logger.info("Supabase client initialized successfully with alternative method")
                    return client
                else:
                    logger.error(f"Unsupported Supabase version: {supabase_version}")
            except Exception as alt_error:
                logger.error(f"Alternative initialization also failed: {alt_error}")
            
            return None
    except Exception as e:
        logger.error(f"Error initializing Supabase: {e}")
        return None