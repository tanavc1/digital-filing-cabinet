# Builder Stage
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runner Stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime libs only
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy Application Code
COPY . .

# Environment Defaults
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose Port
EXPOSE 8000

# Start Command
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
