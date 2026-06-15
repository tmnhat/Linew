#!/bin/bash
# Linew Prediction Worker - Native macOS with MPS Support
# Run this script to start the prediction worker using Apple Silicon GPU (MPS)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Linew Prediction Worker (Native macOS)"
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

# Check MPS availability
echo "Checking GPU/MPS availability..."
python3 << 'EOF'
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"MPS available: {torch.backends.mps.is_available()}")
print(f"MPS built: {torch.backends.mps.is_built()}")
if torch.cuda.is_available():
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"CUDA device: {torch.cuda.get_device_name(0)}")
EOF

echo ""

# Set environment variables for MPS
export PYTORCH_ENABLE_MPS_FALLBACK=1
export MPS_MEMORY_FRACTION=0.8

# Database URL - use Docker postgres
export DATABASE_URL="postgresql+asyncpg://linew:changeme@localhost:5432/linew"
export REDIS_URL="redis://localhost:6379/0"

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if ! nc -z localhost 5432 2>/dev/null; then
    echo "Warning: PostgreSQL not running on localhost:5432"
    echo "Trying to connect via Docker..."
    docker compose exec -T postgres pg_isready -U linew && echo "PostgreSQL is ready (via Docker)"
fi

# Check Redis
echo "Checking Redis connection..."
if ! nc -z localhost 6379 2>/dev/null; then
    echo "Warning: Redis not running on localhost:6379"
    echo "Trying to connect via Docker..."
    docker compose exec -T redis redis-cli ping 2>/dev/null && echo "Redis is ready (via Docker)"
fi

echo ""
echo "============================================"
echo "Starting Prediction Worker with MPS..."
echo "============================================"
echo ""

# Change to project directory
cd "$PROJECT_ROOT"

# Start the worker
exec celery -A app.worker.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=solo \
    --hostname=prediction-worker-mps@%h
