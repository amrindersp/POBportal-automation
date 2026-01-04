#!/bin/bash
# Start the RQ worker in the background
python3 worker.py &
# Start the FastAPI web server in the foreground
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
