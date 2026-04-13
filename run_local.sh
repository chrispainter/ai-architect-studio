#!/bin/bash
echo "================================================"
echo "Starting AI Architect Studio - Local Environment"
echo "================================================"

# Load .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "Loaded .env file"
fi

echo "1. Starting FastAPI Backend Server on port 8000..."
cd backend
if [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

echo "2. Starting React Vite Frontend Server..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "Local Environment Running!"
echo "------------------------------------------------"
echo "View Dashboard: http://localhost:5173"
echo "API Docs (Swagger): http://localhost:8000/docs"
echo "------------------------------------------------"
echo "Type [CTRL+C] at any time to shut down the servers."

trap "echo 'Shutting down servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM EXIT
wait
