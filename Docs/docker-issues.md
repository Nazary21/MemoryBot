# Docker Deployment Issues and Solutions

## Problem

We encountered issues deploying our application to Railway using Docker. The main problem was related to environment variable handling, specifically the `PORT` variable that Railway uses to specify which port the application should listen on.

### Symptoms

1. Deployment fails with error: `Invalid value for '--port': '$PORT' is not a valid integer`
2. The application cannot start because uvicorn cannot parse the port value
3. Health checks fail, causing the deployment to be marked as failed
4. The error occurs despite trying multiple approaches to handle the PORT variable

### Root Cause Analysis

The issue appears to be with how environment variables are passed and interpreted in the Docker container:

1. Railway sets a `PORT` environment variable for the container
2. When using the shell form of CMD in Dockerfile (`CMD uvicorn bot:app --host 0.0.0.0 --port $PORT`), the `$PORT` variable is not being properly substituted with its actual value
3. This results in uvicorn receiving the literal string `$PORT` instead of the numeric value

## Attempted Solutions

### 1. Using a Shell Script (start.sh)

We created a shell script to handle the PORT variable:

```bash
#!/bin/bash
# Set default port if not provided
PORT=${PORT:-8000}
# Start the application
exec uvicorn bot:app --host 0.0.0.0 --port $PORT
```

And modified the Dockerfile to use it:

```dockerfile
COPY . .
RUN chmod +x start.sh
CMD ["./start.sh"]
```

**Result**: Failed - The script was executed but still resulted in the same error.

### 2. Using a Python Script (start.py)

We created a Python script to handle the PORT variable:

```python
import os
import uvicorn
import sys

# Get the PORT environment variable, default to 8000 if not set
port_str = os.environ.get('PORT', '8000')
try:
    # Convert port to integer
    port_int = int(port_str)
    # Start the application using uvicorn's Python API
    if __name__ == "__main__":
        uvicorn.run("bot:app", host="0.0.0.0", port=port_int)
except ValueError as e:
    print(f"ERROR: Could not convert PORT value '{port_str}' to integer: {e}")
    sys.exit(1)
```

And modified the Dockerfile to use it:

```dockerfile
COPY . .
CMD ["python", "start.py"]
```

**Result**: Failed - The script was executed but still encountered issues with the PORT variable.

### 3. Using Shell Form of CMD with Direct Variable Substitution

We modified the Dockerfile to use the shell form of CMD:

```dockerfile
ENV PORT=8000
CMD uvicorn bot:app --host 0.0.0.0 --port $PORT
```

**Result**: Failed - The `$PORT` variable was not properly substituted.

## Current Solution

Our current solution involves multiple components working together:

### 1. Explicitly Setting PORT in Railway Variables

We added the PORT variable directly to Railway's environment variables:
- Key: `PORT`
- Value: `8000`

This ensures that Railway explicitly sets this variable rather than relying on automatic injection.

### 2. Enhanced Entrypoint Script

We created a robust entrypoint script (`entrypoint.sh`) that:
- Prints all environment variables for debugging
- Checks if the PORT variable is set and provides a default if not
- Validates that PORT is a numeric value
- Displays Railway-specific information
- Uses `exec` to properly start the application

```bash
#!/bin/bash
# Check for PORT variable
if [ -z "$PORT" ]; then
  echo "WARNING: PORT environment variable not set, using default port 8000"
  export PORT=8000
fi

# Verify PORT is a number
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo "ERROR: PORT value '$PORT' is not a valid number"
  echo "Setting default PORT=8000"
  export PORT=8000
fi

# Start the application with the resolved port
exec uvicorn bot:app --host 0.0.0.0 --port "$PORT"
```

### 3. Updated Dockerfile Configuration

We modified our Dockerfile to:
- Set a default PORT value that can be overridden
- Use ENTRYPOINT to run our script
- Include clear comments about Railway's environment

```dockerfile
# Set a default PORT environment variable
# This will be overridden by Railway if PORT is set in their variables
ENV PORT=8000

# Use ENTRYPOINT for the script
ENTRYPOINT ["./entrypoint.sh"]
```

**Result**: This approach provides multiple layers of protection against PORT variable issues:
1. Explicit setting in Railway
2. Default value in Dockerfile
3. Validation and fallback in entrypoint script

## Lessons Learned

1. Docker environment variable handling can be tricky, especially when using different forms of the CMD instruction
2. The way environment variables are passed from a platform (like Railway) to a container may not always work as expected
3. It's important to include detailed logging and debugging information when troubleshooting environment variable issues
4. Testing locally with similar environment configurations can help identify issues before deployment
5. Explicitly setting environment variables in both the platform and the container provides more reliable behavior
6. Using an entrypoint script with validation logic adds an extra layer of protection against variable issues 