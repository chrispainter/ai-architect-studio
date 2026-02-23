#!/bin/bash
echo "================================================"
echo "Starting AI Architect Studio - Local Environment"
echo "================================================"

echo "1. Starting FastAPI Backend Server on port 8000..."
source venv/bin/activate
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "2. Starting React Vite Frontend Server..."
export PATH=$PWD/node-v20.18.0-darwin-arm64/bin:$PATH
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "✅ Local Environment Running Successfully!"
echo "------------------------------------------------"
echo "🌐 View Dashboard: http://localhost:5173"
echo "🔌 API Docs (Swagger): http://localhost:8000/docs"
echo "------------------------------------------------"
echo "Type [CTRL+C] at any time to shut down the servers."

trap "echo 'Shutting down servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM EXIT
wait
