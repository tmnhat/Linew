#!/bin/bash
# Linew Native Worker - macOS với MPS Support
# Worker này chạy native trên macOS để tận dụng Apple Silicon GPU

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Linew Native Worker (MPS Support)"
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

# Check MPS
echo ""
echo "=== GPU/MPS Status ==="
python3 << 'EOF'
import torch
print(f"PyTorch: {torch.__version__}")
print(f"MPS Available: {torch.backends.mps.is_available()}")
print(f"MPS Built: {torch.backends.mps.is_built()}")
if torch.backends.mps.is_available():
    print(f"MPS Device Count: {torch.backends.mps.device_count()}")
    # Test MPS tensor
    try:
        x = torch.randn(1000, 1000, device='mps')
        y = torch.mm(x, x)
        print("MPS tensor test: PASSED")
    except Exception as e:
        print(f"MPS tensor test: FAILED - {e}")
EOF

echo ""
echo "=== Environment ==="
echo "DATABASE_URL: postgresql+asyncpg://linew:changeme_secure_password@localhost:5432/linew"
echo "REDIS_URL: redis://localhost:6379/0"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export PYTORCH_ENABLE_MPS_FALLBACK=1
export DATABASE_URL="postgresql+asyncpg://linew:changeme_secure_password@localhost:5432/linew"
export REDIS_URL="redis://localhost:6379/0"
export TIMESFM_DEVICE=mps

echo ""
echo "============================================"
echo "Starting Celery Worker with MPS..."
echo "============================================"
echo ""

cd "$PROJECT_ROOT"

# Start worker
exec celery -A app.worker.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=solo \
    --hostname=native-mps-worker@%h
