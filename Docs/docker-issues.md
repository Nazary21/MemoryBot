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

[To be completed after finding a working solution]

## Lessons Learned

1. Docker environment variable handling can be tricky, especially when using different forms of the CMD instruction
2. The way environment variables are passed from a platform (like Railway) to a container may not always work as expected
3. It's important to include detailed logging and debugging information when troubleshooting environment variable issues
4. Testing locally with similar environment configurations can help identify issues before deployment 