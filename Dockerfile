FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with special handling for supabase
RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "^#" requirements.txt | grep -v "supabase" > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    pip install --no-cache-dir supabase==2.12.0 --no-deps

# Copy entrypoint script first and make it executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy the rest of the application
COPY . .

# Set a default PORT environment variable
ENV PORT=8000

# Use ENTRYPOINT for the script and CMD for default arguments
ENTRYPOINT ["./entrypoint.sh"] 