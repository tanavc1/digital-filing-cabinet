#!/bin/bash

echo "🚀 Building Docker Image..."
docker build -t digital-filing-cabinet-backend .

echo "🐳 Running Container..."
echo "Backend will be at http://localhost:8000"
echo "Press Ctrl+C to stop."

# Run with environment variables passed through or defaults
# Mount lancedb_data to persist data locally during tests
docker run -p 8000:8000 \
  -v $(pwd)/lancedb_data:/app/lancedb_data \
  --env-file .env \
  digital-filing-cabinet-backend
