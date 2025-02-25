FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install dependencies with special handling for supabase
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir $(grep -v "supabase" requirements.txt) && \
    pip install --no-cache-dir supabase==2.12.0 --no-deps

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 