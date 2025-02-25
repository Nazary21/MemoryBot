FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with special handling for supabase
RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "^#" requirements.txt | grep -v "supabase" > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    pip install --no-cache-dir supabase==2.12.0 --no-deps

# Copy start.py first to ensure it's available
COPY start.py .

# Copy the rest of the application
COPY . .

# Use the Python script to start the application
# This bypasses the shell variable substitution issues
CMD ["python", "start.py"]
