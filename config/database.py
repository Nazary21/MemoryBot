import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

def init_supabase():
    """Initialize Supabase client"""
    try:
        logging.info(f"Initializing Supabase client with URL: {SUPABASE_URL[:10]}...")
        
        # Create client with only positional arguments, no keyword args
        # This ensures compatibility with supabase==2.3.1
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        logging.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logging.error(f"Error initializing Supabase: {e}")
        # Log more details about the error for debugging
        logging.error(f"Error type: {type(e)}")
        logging.error(f"Error args: {e.args}")
        # Return None instead of raising to allow the application to continue
        # with limited functionality rather than crashing
        return None