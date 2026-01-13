#!/bin/bash
# Start Backend
echo "Starting Backend on port 8000..."
uvicorn api:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend on port 3000..."
cd frontend
npm run dev -- -p 3000 &
FRONTEND_PID=$!

echo "Pilot running. Backend: http://0.0.0.0:8000/docs | Frontend: http://localhost:3000"
echo "Press CTRL+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
