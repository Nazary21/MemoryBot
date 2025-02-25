#!/bin/bash
# entrypoint.sh - Docker entrypoint script for handling environment variables

# Print environment for debugging
echo "============ ENVIRONMENT VARIABLES ============"
env | sort
echo "==============================================="

# Check for PORT variable
if [ -z "$PORT" ]; then
  echo "WARNING: PORT environment variable not set, using default port 8000"
  export PORT=8000
else
  echo "INFO: Using PORT=$PORT from environment"
fi

# Verify PORT is a number
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo "ERROR: PORT value '$PORT' is not a valid number"
  echo "Setting default PORT=8000"
  export PORT=8000
fi

# Print Railway-specific variables if they exist
if [ ! -z "$RAILWAY_ENVIRONMENT" ]; then
  echo "============ RAILWAY INFORMATION ============"
  echo "RAILWAY_ENVIRONMENT: $RAILWAY_ENVIRONMENT"
  echo "RAILWAY_SERVICE_NAME: $RAILWAY_SERVICE_NAME"
  echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"
  echo "==============================================="
fi

# Print the command we're about to execute
echo "COMMAND: uvicorn bot:app --host 0.0.0.0 --port $PORT"

# Start the application with the resolved port
# Using exec to replace the shell process with uvicorn
# This ensures signals are properly passed to the application
exec uvicorn bot:app --host 0.0.0.0 --port "$PORT" 