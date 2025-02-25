#!/bin/bash
# start.sh - Startup script for the application

# Set default port if not provided
PORT=${PORT:-8000}

# Start the application
exec uvicorn bot:app --host 0.0.0.0 --port $PORT 