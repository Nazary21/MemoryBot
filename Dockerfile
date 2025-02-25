FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with special handling for supabase
RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "^#" requirements.txt | grep -v "supabase" > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    pip install --no-cache-dir supabase==2.12.0 --no-deps

# Copy the Python startup script first
COPY start.py .

# Copy the rest of the application
COPY . .

# Set a default PORT environment variable
# Note: This is just a fallback, Railway should provide the actual PORT value
ENV PORT=8000

# Use Python script to start the application
# This avoids shell variable substitution issues by handling the PORT in Python code
CMD ["sh", "-c", "echo 'ENV VARIABLES:' && env && echo 'Starting app...' && uvicorn bot:app --host 0.0.0.0 --port ${PORT:-8000}"]
