#!/bin/bash
# WinterStream AI - Development Startup Script (Bash)
# Run this script to start both backend and frontend servers

echo "🏂 Starting WinterStream AI Development Environment"
echo ""

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Python virtual environment exists
if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv "$SCRIPT_DIR/backend/venv"
fi

# Start Backend
echo -e "${GREEN}Starting Backend Server (FastAPI)...${NC}"
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Frontend
echo -e "${GREEN}Starting Frontend Server (Next.js)...${NC}"
cd "$SCRIPT_DIR/frontend"
npm install
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}✨ Development servers started!${NC}"
echo ""
echo "Backend API: http://localhost:8000"
echo "Frontend:    http://localhost:3000"
echo "API Docs:    http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
