FROM python:3.11-slim-bookworm

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    BACKEND_URL=http://127.0.0.1:8000 \
    SPACY_MODEL=en_core_web_sm \
    GROQ_MODEL=openai/gpt-oss-20b

WORKDIR /app

# Install system dependencies for WeasyPrint, PDF tools, and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU and Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Pre-download SentenceTransformer model weights into Docker image for 0s startup latency
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', device='cpu')"

# Copy application code
COPY . .

# Set execution permissions on start script
RUN chmod +x start.sh

# Expose ports
EXPOSE 8501 8000

# Start both FastAPI backend and Streamlit frontend
CMD ["./start.sh"]
