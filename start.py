import os
import uvicorn
import sys

# Get the PORT environment variable, default to 8000 if not set
port_str = os.environ.get('PORT', '8000')

# Print debug information
print(f"PORT environment variable: {port_str!r}")
print(f"PORT type: {type(port_str)}")
print(f"All environment variables: {list(os.environ.keys())}")

try:
    # Convert port to integer
    port_int = int(port_str)
    print(f"Converted PORT to integer: {port_int}")
    
    # Start the application using uvicorn's Python API
    if __name__ == "__main__":
        print(f"Starting uvicorn with host='0.0.0.0', port={port_int}")
        uvicorn.run("bot:app", host="0.0.0.0", port=port_int)
except ValueError as e:
    print(f"ERROR: Could not convert PORT value '{port_str}' to integer: {e}")
    print(f"Python version: {sys.version}")
    sys.exit(1)