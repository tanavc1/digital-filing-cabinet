# Base Image
FROM python:3.11-slim

# Working Directory
WORKDIR /app

# System Dependencies (minimal for building python extensions if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Application Code
COPY . .

# Environment Defaults
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose Port
EXPOSE 8000

# Start Command
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
