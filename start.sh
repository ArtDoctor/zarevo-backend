#!/bin/bash

# Exit on error
set -e

set -a
source .env
set +a

source venv/bin/activate

echo "Starting Celery worker in the background..."
celery -A worker.worker -q worker --loglevel=info &
CELERY_PID=$!

echo "Starting FastAPI server..."
uvicorn src.main:app --host 0.0.0.0 --port 26769 --reload

# Trap SIGINT (Ctrl+C) to kill both processes
trap "kill $CELERY_PID" EXIT
