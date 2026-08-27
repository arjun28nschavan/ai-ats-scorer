import os
import sys
import time
import subprocess
import signal

def main():
    print("=== Launching AI-ATS-Scorer on Hugging Face Spaces (16GB RAM) ===")

    # Ensure spaCy model is installed
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except Exception:
        print("Downloading spaCy en_core_web_sm model...")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)

    # 1. Start FastAPI Backend on port 8000
    print("Starting FastAPI backend on port 8000...")
    backend_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ])

    # Wait for backend health check
    time.sleep(3)

    # 2. Start Streamlit Frontend on port 7860 (Hugging Face default)
    port = os.getenv("PORT", "7860")
    print(f"Starting Streamlit frontend on port {port}...")
    frontend_proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--server.headless", "true"
    ])

    def signal_handler(sig, frame):
        print("Shutting down servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    frontend_proc.wait()
    backend_proc.wait()

if __name__ == "__main__":
    main()
