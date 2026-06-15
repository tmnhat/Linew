#!/bin/bash
# Linew Native Beat Scheduler - macOS với MPS Support
# Beat scheduler này chạy native trên macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Linew Native Beat Scheduler"
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
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export PYTORCH_ENABLE_MPS_FALLBACK=1
export DATABASE_URL="postgresql+asyncpg://linew:changeme_secure_password@localhost:5432/linew"
export REDIS_URL="redis://localhost:6379/0"
export TIMESFM_DEVICE=mps

echo ""
echo "=== Environment ==="
echo "DATABASE_URL: postgresql+asyncpg://linew:changeme_secure_password@localhost:5432/linew"
echo "REDIS_URL: redis://localhost:6379/0"

echo ""
echo "============================================"
echo "Starting Beat Scheduler..."
echo "============================================"
echo ""

cd "$PROJECT_ROOT"

# Start beat scheduler
exec celery -A app.worker.celery_app beat \
    --loglevel=info \
    --scheduler=celery.beat:PersistentScheduler
