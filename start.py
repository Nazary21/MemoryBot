import os
import sys
import uvicorn

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
    uvicorn.run("bot:app", host="0.0.0.0", port=port)