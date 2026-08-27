#!/bin/bash
set -e

# Start FastAPI backend on internal loopback (127.0.0.1:8000)
echo "Starting FastAPI Backend on 127.0.0.1:8000..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for FastAPI Backend to be ready
echo "Waiting for FastAPI Backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/v1/health | grep -q "healthy"; then
        echo "FastAPI Backend is ready!"
        break
    fi
    sleep 1
done

# Set default port to 8501 (or $PORT if set by container host)
PORT="${PORT:-8501}"
echo "Starting Streamlit Frontend on port $PORT..."
python -m streamlit run frontend/streamlit_app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

trap "kill -TERM $BACKEND_PID $STREAMLIT_PID" SIGTERM SIGINT

wait -n $STREAMLIT_PID $BACKEND_PID
