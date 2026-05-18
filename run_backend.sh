#!/bin/bash

echo "🔄 Preparing backend environment..."

# Safely kill any ghost python process holding port 8000
if fuser 8000/tcp >/dev/null 2>&1; then
    echo "⚠️ Port 8000 is currently in use. Shutting down the old instance..."
    fuser -k 8000/tcp 2>/dev/null
    sleep 2
fi

echo "🚀 Starting FastAPI Backend on http://0.0.0.0:8000"

# Assuming the script is run from the project root where 'venv' is located
if [ -d "venv" ]; then
    source venv/bin/activate
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "❌ Error: Could not find 'venv' directory. Are you in the right folder?"
    exit 1
fi
