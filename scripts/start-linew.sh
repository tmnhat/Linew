#!/bin/bash
# Linew Quick Start Script
# Khởi động nhanh toàn bộ hệ thống Linew

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           LINEW - AI Media Platform Quick Start              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored status
status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to project directory
cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f ".env" ]; then
    warn "File .env not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn "Please edit .env and configure your settings before running again!"
    else
        error ".env.example not found. Cannot create .env"
        exit 1
    fi
fi

# Parse command line arguments
MODE="${1:-docker}"
FORCE="${2:-}"

usage() {
    echo "Usage: $0 [mode] [options]"
    echo ""
    echo "Modes:"
    echo "  docker    Start with Docker Compose (default)"
    echo "  native    Start native (macOS/Apple Silicon)"
    echo "  status    Check status of running services"
    echo "  stop      Stop all services"
    echo "  logs      Show logs"
    echo "  restart   Restart all services"
    echo ""
    echo "Options:"
    echo "  --force   Force restart even if running"
    echo ""
    echo "Examples:"
    echo "  $0 docker        # Start with Docker"
    echo "  $0 native        # Start native on macOS"
    echo "  $0 status        # Check status"
    echo "  $0 logs worker   # Show worker logs"
}

# Handle different modes
case "$MODE" in
    docker)
        status "Starting Linew with Docker Compose..."
        
        # Check if Docker is running
        if ! docker info > /dev/null 2>&1; then
            error "Docker is not running. Please start Docker first."
            exit 1
        fi
        
        # Build images if needed
        if [ -n "$FORCE" ] || [ ! -f ".docker-built" ]; then
            status "Building Docker images..."
            docker-compose build --parallel 2>&1 | tail -5
            touch .docker-built
        fi
        
        # Start services
        status "Starting services..."
        docker-compose up -d
        
        # Wait for services to be ready
        echo ""
        status "Waiting for services to be ready..."
        sleep 5
        
        # Check service health
        echo ""
        status "Checking service status..."
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep linew || true
        
        echo ""
        success "Linew is starting!"
        echo ""
        echo -e "  ${GREEN}Dashboard:${NC}  http://localhost"
        echo -e "  ${GREEN}API:${NC}         http://localhost:8000"
        echo -e "  ${GREEN}API Docs:${NC}    http://localhost:8000/docs"
        echo -e "  ${GREEN}WordPress:${NC}   http://localhost:8888"
        echo ""
        warn "Allow 10-30 seconds for services to fully initialize."
        ;;
        
    native)
        status "Starting Linew Native (macOS with MPS)..."
        
        # Check for virtual environment
        if [ ! -d "venv" ]; then
            error "Virtual environment not found. Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
            exit 1
        fi
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Check Redis
        if ! nc -z localhost 6379 2>/dev/null; then
            warn "Redis not running. Starting Redis..."
            if command -v redis-server &> /dev/null; then
                redis-server --daemonize yes 2>/dev/null || warn "Could not start Redis automatically"
            else
                warn "Redis not installed. Start Redis manually or use Docker."
            fi
        fi
        
        # Check PostgreSQL
        if ! nc -z localhost 5432 2>/dev/null; then
            warn "PostgreSQL not running. Start PostgreSQL manually or use Docker."
        fi
        
        # Set environment variables
        export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
        export PYTORCH_ENABLE_MPS_FALLBACK=1
        export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://linew:changeme_secure_password@localhost:5432/linew}"
        export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
        export TIMESFM_DEVICE="${TIMESFM_DEVICE:-mps}"
        
        echo ""
        status "Starting services in separate terminals..."
        echo ""
        echo "Terminal 1 - API Server:"
        echo "  cd $PROJECT_ROOT && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        echo ""
        echo "Terminal 2 - Celery Worker:"
        echo "  cd $PROJECT_ROOT && source venv/bin/activate && celery -A app.worker.celery_app worker -l info -c 2 --pool=solo"
        echo ""
        echo "Terminal 3 - Celery Beat (Scheduler):"
        echo "  cd $PROJECT_ROOT && source venv/bin/activate && celery -A app.worker.celery_app beat -l info"
        echo ""
        warn "Open 3 terminal windows and run the commands above."
        ;;
        
    status)
        status "Checking Linew service status..."
        echo ""
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | grep linew || echo "No Linew containers running"
        echo ""
        status "API Health:"
        curl -s http://localhost:8000/api/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "API not responding"
        ;;
        
    stop)
        status "Stopping Linew services..."
        docker-compose down 2>/dev/null || true
        success "Linew stopped."
        ;;
        
    restart)
        status "Restarting Linew services..."
        docker-compose restart
        success "Linew restarted."
        ;;
        
    logs)
        SERVICE="${3:-api}"
        status "Showing logs for $SERVICE..."
        docker logs -f linew-$SERVICE-1 2>&1 | head -100
        ;;
        
    continuous)
        status "Starting Continuous Pipeline Mode..."
        
        # Check if pipeline is already running
        RESPONSE=$(curl -s http://localhost:8000/api/pipeline/info 2>/dev/null || echo '{"is_running":false}')
        IS_RUNNING=$(echo "$RESPONSE" | python3 -c "import sys,json; print('true' if json.load(sys.stdin).get('is_running',False) else 'false')" 2>/dev/null || echo "false")
        
        if [ "$IS_RUNNING" = "true" ]; then
            warn "Pipeline is already running!"
            echo "Current status:"
            curl -s http://localhost:8000/api/pipeline/info | python3 -m json.tool
            echo ""
            read -p "Stop current pipeline and start continuous? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 0
            fi
            curl -s -X POST http://localhost:8000/api/pipeline/stop | python3 -m json.tool
            sleep 2
        fi
        
        status "Starting continuous pipeline..."
        RESPONSE=$(curl -s -X POST http://localhost:8000/api/pipeline/continuous/start \
            -H "Content-Type: application/json" \
            -d '{"limit": 10}' | python3 -m json.tool)
        
        echo "$RESPONSE"
        
        if echo "$RESPONSE" | grep -q '"success": true'; then
            success "Continuous pipeline started!"
            echo ""
            echo "Monitor at: http://localhost/#/pipeline"
            echo "Or check status with:"
            echo "  curl http://localhost:8000/api/pipeline/info"
        else
            error "Failed to start continuous pipeline"
        fi
        ;;
        
    -h|--help|help)
        usage
        ;;
        
    *)
        error "Unknown mode: $MODE"
        usage
        exit 1
        ;;
esac
