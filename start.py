import os
import sys
import logging
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup")

# Print debugging information
logger.info("============ PYTHON ENVIRONMENT INFO ============")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Files in current directory: {os.listdir('.')}")
logger.info("===============================================")

# Print all environment variables
logger.info("============ ENVIRONMENT VARIABLES ============")
for key, value in sorted(os.environ.items()):
    logger.info(f"{key}: {value}")
logger.info("===============================================")

# Get the PORT environment variable, default to 8000 if not set
port_str = os.environ.get('PORT', '8000')
logger.info(f"Raw PORT value: '{port_str}'")

# Handle special case where PORT is literally '$PORT'
if port_str == '$PORT':
    logger.info("Detected literal '$PORT' string - using default port 8000")
    port = 8000
else:
    # Ensure PORT is a valid integer
    try:
        port = int(port_str)
        logger.info(f"Converted PORT to integer: {port}")
    except ValueError:
        logger.error(f"Could not convert PORT value '{port_str}' to integer")
        logger.info("Using default port 8000")
        port = 8000

# Print Railway-specific information if available
if 'RAILWAY_ENVIRONMENT' in os.environ:
    logger.info("============ RAILWAY INFORMATION ============")
    logger.info(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'N/A')}")
    logger.info(f"RAILWAY_SERVICE_NAME: {os.environ.get('RAILWAY_SERVICE_NAME', 'N/A')}")
    logger.info(f"RAILWAY_PUBLIC_DOMAIN: {os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'N/A')}")
    logger.info("===============================================")

# Start the application
if __name__ == "__main__":
    try:
        # Check if bot.py exists
        if not os.path.exists('bot.py'):
            logger.error("bot.py not found in current directory!")
            logger.error(f"Files in directory: {os.listdir('.')}")
            sys.exit(1)
            
        # Import the app using importlib
        logger.info("Attempting to import bot module...")
        
        try:
            # First try direct import
            logger.info("Trying direct import...")
            import bot
            app = bot.app
            logger.info("Successfully imported bot.app via direct import")
        except ImportError as e:
            logger.warning(f"Direct import failed: {e}")
            
            # Fall back to importlib if direct import fails
            logger.info("Falling back to importlib...")
            spec = importlib.util.spec_from_file_location("bot", "bot.py")
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)
            
            # Get the app from the module
            app = bot_module.app
            logger.info("Successfully imported bot.app via importlib")
        
        # Import uvicorn here to avoid any potential issues
        import uvicorn
        
        # Use uvicorn's Python API directly instead of the command-line interface
        logger.info(f"Starting uvicorn with app object directly on port {port}")
        
        # Configure and run the server
        config = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"ERROR starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)