import os
from dotenv import load_dotenv
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

def init_supabase():
    """Initialize Supabase client"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
            return None
            
        logger.info(f"Initializing Supabase client with URL: {SUPABASE_URL[:10]}...")
        
        # Try the simplest initialization first
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully with create_client")
            
            # Test connection
            try:
                test_result = client.table('accounts').select('count(*)', count='exact').limit(1).execute()
                logger.info("Supabase connection test successful")
            except Exception as test_error:
                logger.warning(f"Supabase connection test failed: {test_error}")
                
            return client
        except Exception as e:
            logger.warning(f"Standard initialization failed: {e}")
            
            # Try direct Client import
            try:
                logger.info("Trying direct Client import...")
                from supabase import Client
                client = Client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Direct Client import successful")
                return client
            except Exception as client_error:
                logger.warning(f"Direct Client import failed: {client_error}")
                
                # Try with postgrest
                try:
                    logger.info("Trying with postgrest...")
                    import httpx
                    from supabase.lib.client_options import ClientOptions
                    
                    # Check supabase version
                    import supabase
                    logger.info(f"Supabase version: {getattr(supabase, '__version__', 'unknown')}")
                    
                    # Try to create a minimal client
                    if hasattr(supabase, 'Client'):
                        client = supabase.Client(SUPABASE_URL, SUPABASE_KEY)
                    else:
                        # For older versions
                        from supabase import create_client
                        client = create_client(SUPABASE_URL, SUPABASE_KEY)
                        
                    logger.info("Postgrest approach successful")
                    return client
                except Exception as postgrest_error:
                    logger.error(f"Postgrest approach failed: {postgrest_error}")
        
        # If all attempts fail
        logger.error("All Supabase initialization attempts failed")
        return None
    except Exception as e:
        logger.error(f"Error initializing Supabase: {e}")
        return None