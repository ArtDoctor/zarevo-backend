#!/bin/bash
set -e

[ -f .env ] && set -a && source .env && set +a

echo "Starting Celery worker..."
celery -A worker.worker worker --loglevel=info &
CELERY_PID=$!

trap "kill $CELERY_PID 2>/dev/null || true; exit" EXIT TERM INT

echo "Starting FastAPI server..."
PORT=${PORT:-9076}
uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
