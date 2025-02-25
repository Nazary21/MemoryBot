#!/bin/bash
# entrypoint.sh - Docker entrypoint script for handling environment variables

# Print environment for debugging
echo "Environment variables:"
env | sort

# Set default port if not provided
if [ -z "$PORT" ]; then
  echo "PORT environment variable not set, using default port 8000"
  PORT=8000
else
  echo "Using PORT=$PORT from environment"
fi

# Print the command we're about to execute
echo "Executing: uvicorn bot:app --host 0.0.0.0 --port $PORT"

# Start the application with the resolved port
exec uvicorn bot:app --host 0.0.0.0 --port "$PORT" 