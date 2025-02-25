import os
import sys
import uvicorn
import importlib.util

# Print debugging information
print("============ PYTHON ENVIRONMENT INFO ============")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")
print("===============================================")

# Print all environment variables
print("============ ENVIRONMENT VARIABLES ============")
for key, value in sorted(os.environ.items()):
    print(f"{key}: {value}")
print("===============================================")

# Get the PORT environment variable, default to 8000 if not set
port_str = os.environ.get('PORT', '8000')
print(f"Raw PORT value: '{port_str}'")

# Handle special case where PORT is literally '$PORT'
if port_str == '$PORT':
    print("Detected literal '$PORT' string - using default port 8000")
    port = 8000
else:
    # Ensure PORT is a valid integer
    try:
        port = int(port_str)
        print(f"Converted PORT to integer: {port}")
    except ValueError:
        print(f"ERROR: Could not convert PORT value '{port_str}' to integer")
        print("Using default port 8000")
        port = 8000

# Print Railway-specific information if available
if 'RAILWAY_ENVIRONMENT' in os.environ:
    print("============ RAILWAY INFORMATION ============")
    print(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'N/A')}")
    print(f"RAILWAY_SERVICE_NAME: {os.environ.get('RAILWAY_SERVICE_NAME', 'N/A')}")
    print(f"RAILWAY_PUBLIC_DOMAIN: {os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'N/A')}")
    print("===============================================")

# Print the command we're about to execute
print(f"Starting uvicorn with host='0.0.0.0', port={port}")

# Start the application
if __name__ == "__main__":
    try:
        # Import the app directly instead of using string reference
        print("Attempting to import bot module...")
        
        # Check if bot.py exists
        if not os.path.exists('bot.py'):
            print("ERROR: bot.py not found in current directory!")
            print(f"Files in directory: {os.listdir('.')}")
            sys.exit(1)
            
        # Import the app using importlib
        spec = importlib.util.spec_from_file_location("bot", "bot.py")
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        # Get the app from the module
        app = bot_module.app
        print("Successfully imported bot.app")
        
        # Run using uvicorn's run function with the app object directly
        print(f"Starting uvicorn with app object directly on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"ERROR starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)