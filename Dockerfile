FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with special handling for supabase
RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "^#" requirements.txt | grep -v "supabase" > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt && \
    pip install --no-cache-dir supabase==2.12.0 --no-deps

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy the rest of the application
COPY . .

# Set a default PORT environment variable
# Note: This is just a fallback, Railway should provide the actual PORT value
ENV PORT=8000

# Force shell expansion by using sh -c
ENTRYPOINT ["sh", "-c", "/entrypoint.sh"]
