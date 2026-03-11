#!/bin/bash

# ALSP Pipeline - Perfect Demo Launcher
# ======================================

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   ALSP PIPELINE - DEMO LAUNCHER 🚀    ${NC}"
echo -e "${BLUE}=======================================${NC}"

# 1. Check Prereqs
echo -e "\n${GREEN}[1/5] Checking environment...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${RED}Error: Ollama is not running!${NC}"
    echo "Please start Ollama.app or run 'ollama serve' in another terminal."
    exit 1
fi
echo "✓ Ollama is running"

if ! pgrep -x "docker" > /dev/null && ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Warning: Docker is not running (needed for OCR/Docling).${NC}"
    # Continuing anyway as we might rely on text fallback or local deps
fi

# 2. Cleanup Old Processes
echo -e "\n${GREEN}[2/5] Cleaning up existing processes...${NC}"
lsof -t -i :8000 | xargs kill -9 2>/dev/null
lsof -t -i :3000 | xargs kill -9 2>/dev/null
echo "✓ Ports 8000 (API) and 3000 (UI) cleared"

# 3. Create Golden Dataset (Just in case)
echo -e "\n${GREEN}[3/5] Protecting Golden Dataset...${NC}"
python3 generate_golden_dataset.py
echo "✓ golden_demo_dataset.zip is ready"

# 4. Start Backend
echo -e "\n${GREEN}[4/5] Starting Backend Server...${NC}"
export OFFLINE_MODE=true 
export LLM_PROVIDER=ollama 
export OLLAMA_MODEL=phi4-mini
export OLLAMA_VISION_MODEL=qwen3-vl:8b

# Run in background
/opt/anaconda3/bin/python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID). Logs -> backend.log"

# Wait for health check
echo "Waiting for backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✓ Backend is healthy!"
        break
    fi
    sleep 1
    echo -n "."
done

# 5. Start Frontend
echo -e "\n${GREEN}[5/5] Starting Frontend...${NC}"
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "✓ Frontend started (PID: $FRONTEND_PID). Logs -> frontend.log"

echo -e "\n${BLUE}=======================================${NC}"
echo -e "${GREEN}   DEMO IS LIVE! GO GO GO! 🎬          ${NC}"
echo -e "${BLUE}   Open: http://localhost:3000         ${NC}"
echo -e "${BLUE}=======================================${NC}"
echo "Press CTRL+C to stop servers."

# Keep script running to trap exit
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
