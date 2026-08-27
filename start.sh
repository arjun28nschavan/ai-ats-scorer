#!/bin/bash
set -e

echo "Starting FastAPI Backend on port 8000..."
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Waiting for FastAPI Backend to be healthy..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/v1/health | grep -q "healthy"; then
        echo "FastAPI Backend is ready!"
        break
    fi
    sleep 1
done

# Default port to 7860 (Hugging Face Spaces default), 10000 (Render), or 8501
PORT="${PORT:-7860}"
echo "Starting Streamlit Frontend on port $PORT..."
streamlit run frontend/streamlit_app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

trap "kill -TERM $BACKEND_PID $STREAMLIT_PID" SIGTERM SIGINT

wait $STREAMLIT_PID $BACKEND_PID
