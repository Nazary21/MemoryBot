import os
import sys
import subprocess

# Get the PORT environment variable, default to 8000 if not set
port = os.environ.get('PORT', '8000')

# Print debug information
print(f"Starting application with PORT={port}")
print(f"Environment variables: {dict(os.environ)}")

# Start the application
cmd = ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", port]
print(f"Running command: {' '.join(cmd)}")
subprocess.run(cmd) 