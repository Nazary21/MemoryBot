import os
import uvicorn

# Get the PORT environment variable, default to 8000 if not set
port = os.environ.get('PORT', '8000')

# Print debug information
print(f"Starting application with PORT={port}")
print(f"Environment variables: {dict(os.environ)}")

# Convert port to integer
port_int = int(port)
print(f"Converted PORT to integer: {port_int}")

# Start the application using uvicorn's Python API
if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=port_int) 