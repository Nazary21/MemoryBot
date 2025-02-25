#!/bin/bash
# entrypoint.sh - Docker entrypoint script for handling environment variables

# Print environment for debugging
echo "============ ENVIRONMENT VARIABLES ============"
env | sort
echo "==============================================="

# Ensure PORT is set correctly
PORT=${PORT:-8000}  # Default to 8000 if not set

echo "============ DEBUGGING PORT VARIABLE ============"
echo "Raw PORT value: '$PORT'"
echo "Expanded PORT value: $(echo $PORT)"
echo "Checking if PORT is a number..."
echo "$PORT" | grep -E '^[0-9]+$' > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: PORT is not a valid number! Setting default to 8000."
  PORT=8000
else
  echo "✅ PORT is valid: $PORT"
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
echo "Starting Uvicorn on PORT=$PORT"

# Start the application with the resolved port
# Using exec to replace the shell process with uvicorn
# This ensures signals are properly passed to the application
echo "============ STARTING UVICORN ============"
echo "Using hardcoded port 8000 instead of environment variable"
exec uvicorn bot:app --host 0.0.0.0 --port 8000 