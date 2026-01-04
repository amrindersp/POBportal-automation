#!/bin/bash
# Start the RQ worker in the background
python worker.py &
# Start the FastAPI web server in the foreground
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
