#!/bin/bash
# Linew Beat Scheduler - Native macOS with MPS Support
# Run this script to start the beat scheduler for prediction tasks

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Linew Beat Scheduler (Native macOS)"
echo "============================================"
echo ""

# Activate virtual environment
VENV_PATH="$PROJECT_ROOT/venv"
if [ -d "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Set environment variables
export PYTORCH_ENABLE_MPS_FALLBACK=1
export DATABASE_URL="postgresql+asyncpg://linew:changeme@localhost:5432/linew"
export REDIS_URL="redis://localhost:6379/0"

echo "============================================"
echo "Starting Beat Scheduler..."
echo "============================================"
echo ""

# Change to project directory
cd "$PROJECT_ROOT"

# Start beat scheduler
exec celery -A app.worker.celery_app beat \
    --loglevel=info \
    --scheduler=celery.beat:Scheduler
