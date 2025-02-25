FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with special handling for supabase
RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "^#" requirements.txt | grep -v "supabase" > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    pip install --no-cache-dir supabase==2.12.0 --no-deps

COPY . .

# Set a default PORT environment variable
ENV PORT=8000

# Use shell form of CMD to allow environment variable substitution
# This directly executes uvicorn with the PORT variable
CMD uvicorn bot:app --host 0.0.0.0 --port $PORT 