#!/bin/bash
# ============================================
# Digital Filing Cabinet — One-Click Setup
# ============================================
# This script installs everything needed to run
# the Digital Filing Cabinet locally on your machine.
#
# Usage: ./setup.sh
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo ""
echo -e "${BOLD}📁 Digital Filing Cabinet — Setup${NC}"
echo "=================================="
echo ""

# ----------------------------
# 1. Check Python
# ----------------------------
echo -e "${BLUE}[1/6]${NC} Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION found"
else
    echo -e "  ${RED}✗${NC} Python 3.10+ is required."
    echo "  Install from: https://www.python.org/downloads/"
    exit 1
fi

# ----------------------------
# 2. Check Node.js
# ----------------------------
echo -e "${BLUE}[2/6]${NC} Checking Node.js..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo -e "  ${GREEN}✓${NC} Node.js $NODE_VERSION found"
else
    echo -e "  ${RED}✗${NC} Node.js 18+ is required."
    echo "  Install from: https://nodejs.org/"
    exit 1
fi

# ----------------------------
# 3. Install Ollama (if needed)
# ----------------------------
echo -e "${BLUE}[3/6]${NC} Checking Ollama..."
if command -v ollama &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Ollama is installed"
else
    echo -e "  ${YELLOW}→${NC} Installing Ollama..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &>/dev/null; then
            brew install ollama
        else
            echo -e "  ${YELLOW}→${NC} Downloading Ollama for macOS..."
            curl -fsSL https://ollama.com/install.sh | sh
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo -e "  ${RED}✗${NC} Please install Ollama manually: https://ollama.com"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Ollama installed"
fi

# Ensure Ollama is running
echo -e "  ${YELLOW}→${NC} Starting Ollama service..."
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    ollama serve &>/dev/null &
    sleep 3
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama service started"
    else
        echo -e "  ${YELLOW}!${NC} Could not auto-start Ollama. Please run 'ollama serve' in another terminal."
    fi
else
    echo -e "  ${GREEN}✓${NC} Ollama is already running"
fi

# ----------------------------
# 4. Pull AI Models
# ----------------------------
echo -e "${BLUE}[4/6]${NC} Pulling local AI models (this may take a few minutes on first run)..."

echo -e "  ${YELLOW}→${NC} Pulling phi4-mini (text LLM, ~2.5GB)..."
ollama pull phi4-mini 2>/dev/null && echo -e "  ${GREEN}✓${NC} phi4-mini ready" || echo -e "  ${YELLOW}!${NC} phi4-mini pull failed — you can retry with: ollama pull phi4-mini"

echo -e "  ${YELLOW}→${NC} Pulling qwen3-vl:8b (vision LLM, ~5GB)..."
ollama pull qwen3-vl:8b 2>/dev/null && echo -e "  ${GREEN}✓${NC} qwen3-vl:8b ready" || echo -e "  ${YELLOW}!${NC} qwen3-vl pull failed — you can retry with: ollama pull qwen3-vl:8b"

# ----------------------------
# 5. Install Dependencies
# ----------------------------
echo -e "${BLUE}[5/6]${NC} Installing dependencies..."

# Python
echo -e "  ${YELLOW}→${NC} Installing Python packages..."
pip3 install -r requirements.txt --quiet 2>&1 | tail -1
echo -e "  ${GREEN}✓${NC} Python dependencies installed"

# Frontend
echo -e "  ${YELLOW}→${NC} Installing frontend packages..."
cd frontend
npm install --silent 2>&1 | tail -1
cd ..
echo -e "  ${GREEN}✓${NC} Frontend dependencies installed"

# ----------------------------
# 6. Create Config Files
# ----------------------------
echo -e "${BLUE}[6/6]${NC} Setting up configuration..."

# Backend .env
if [ ! -f .env ]; then
    cat > .env << 'EOF'
DB_PATH=./lancedb_data
LLM_PROVIDER=ollama
OLLAMA_MODEL=phi4-mini
VISION_PROVIDER=ollama
OLLAMA_VISION_MODEL=qwen3-vl:8b
ADMIN_PASSWORD=changeme
EOF
    echo -e "  ${GREEN}✓${NC} Created .env (backend config)"
else
    echo -e "  ${YELLOW}!${NC} .env already exists — skipping"
fi

# Frontend .env.local
if [ ! -f frontend/.env.local ]; then
    cat > frontend/.env.local << 'EOF'
ADMIN_PASSWORD="changeme"
AUTH_SECRET="$(openssl rand -base64 32)"
NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
EOF
    echo -e "  ${GREEN}✓${NC} Created frontend/.env.local"
else
    echo -e "  ${YELLOW}!${NC} frontend/.env.local already exists — skipping"
fi

# ----------------------------
# Done!
# ----------------------------
echo ""
echo -e "${GREEN}${BOLD}✓ Setup complete!${NC}"
echo ""
echo -e "  To start the application:"
echo ""
echo -e "    ${BOLD}sh scripts/start_pilot.sh${NC}"
echo ""
echo -e "  Then open ${BOLD}http://localhost:3000${NC} in your browser."
echo -e "  Default password: ${BOLD}changeme${NC} (change in .env)"
echo ""
echo -e "  ${YELLOW}Models running locally:${NC}"
echo -e "    • Text LLM:    phi4-mini (via Ollama)"
echo -e "    • Vision LLM:  qwen3-vl:8b (via Ollama)"
echo -e "    • Embeddings:  BAAI/bge-small-en-v1.5 (auto-downloaded)"
echo -e "    • Reranker:    ms-marco-MiniLM-L-6-v2 (auto-downloaded)"
echo ""
echo -e "  ${GREEN}No API keys needed. Everything runs on your machine.${NC}"
echo ""
