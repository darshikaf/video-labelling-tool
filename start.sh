#!/bin/bash

set -e

echo "=========================================="
echo "Medical Video Annotation Tool"
echo "Development Environment Setup"
echo "=========================================="
echo ""

# Function to detect Docker Compose command
get_docker_compose_cmd() {
    # Prefer 'docker compose' (v2) over 'docker-compose' (v1)
    if docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null 2>&1; then
    echo "Error: Docker daemon is not running"
    echo "Please start Docker Desktop or the Docker service"
    exit 1
fi

# Get the appropriate Docker Compose command
DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
if [ -z "$DOCKER_COMPOSE_CMD" ]; then
    echo "Error: Neither 'docker compose' nor 'docker-compose' is available"
    echo "Please ensure Docker Compose is installed"
    exit 1
fi
echo "✓ Using Docker Compose: $DOCKER_COMPOSE_CMD"

# Create required directories
mkdir -p uploads models exports
echo "✓ Created required directories (uploads, models, exports)"

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Created .env file from .env.example"
    else
        echo "Warning: No .env.example found, creating minimal .env"
        cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:postgres@database:5432/video_annotation
REDIS_URL=redis://redis:6379/0
SAM_SERVICE_URL=http://sam-service:8001
UPLOAD_DIR=/app/uploads
JWT_SECRET_KEY=dev-secret-key-change-in-production
EOF
        echo "✓ Created minimal .env file"
    fi
else
    echo "✓ .env file already exists"
fi

# Detect platform and start appropriate services
PLATFORM=$(uname -m)
OS=$(uname -s)

# Set TARGETPLATFORM environment variable for Docker builds
case "$PLATFORM-$OS" in
    "arm64-Darwin")
        export TARGETPLATFORM="linux/arm64"
        PLATFORM_NAME="macOS Apple Silicon (ARM64)"
        DEFAULT_MODE="multi"
        ;;
    "x86_64-Darwin")
        export TARGETPLATFORM="linux/amd64"
        PLATFORM_NAME="macOS Intel (x86_64)"
        DEFAULT_MODE="multi"
        ;;
    "x86_64-Linux")
        export TARGETPLATFORM="linux/amd64"
        PLATFORM_NAME="Linux x86_64"
        DEFAULT_MODE="cpu"
        ;;
    "aarch64-Linux")
        export TARGETPLATFORM="linux/arm64"
        PLATFORM_NAME="Linux ARM64"
        DEFAULT_MODE="multi"
        ;;
    *)
        export TARGETPLATFORM="linux/amd64"
        PLATFORM_NAME="Unknown (defaulting to AMD64)"
        DEFAULT_MODE="cpu"
        ;;
esac

echo "✓ Detected platform: $PLATFORM_NAME"
echo "✓ Docker target platform: $TARGETPLATFORM"
echo ""

# Parse command line arguments
MODE="$DEFAULT_MODE"
BUILD_ARG=""
DETACH="-d"

while [[ $# -gt 0 ]]; do
    case $1 in
        --cpu)
            MODE="cpu"
            shift
            ;;
        --gpu)
            MODE="multi"
            shift
            ;;
        --build)
            BUILD_ARG="--build"
            shift
            ;;
        --foreground|-f)
            DETACH=""
            shift
            ;;
        --down|--stop)
            echo "Stopping all services..."
            $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml down
            echo "✓ All services stopped"
            exit 0
            ;;
        --logs)
            SERVICE="${2:-}"
            if [ -n "$SERVICE" ]; then
                $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml logs -f "$SERVICE"
            else
                $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml logs -f
            fi
            exit 0
            ;;
        --status)
            $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml ps
            exit 0
            ;;
        --help|-h)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cpu          Force CPU-only mode (no GPU)"
            echo "  --gpu          Force GPU/multi-platform mode"
            echo "  --build        Force rebuild of all containers"
            echo "  --foreground   Run in foreground (show logs)"
            echo "  --down/--stop  Stop all services"
            echo "  --logs [svc]   Show logs (optionally for specific service)"
            echo "  --status       Show status of all services"
            echo "  --help         Show this help message"
            echo ""
            echo "Platform auto-detection:"
            echo "  - macOS (Intel/ARM): Multi-platform mode"
            echo "  - Linux x86_64: CPU-only mode (default)"
            echo "  - Linux ARM64: Multi-platform mode"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Choose configuration based on mode
echo "Starting services in $MODE mode..."
echo ""

if [[ "$MODE" == "cpu" ]]; then
    echo "Using CPU-only configuration..."
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml -f docker-compose.cpu.yml up $BUILD_ARG $DETACH
else
    echo "Using multi-platform configuration..."
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml up $BUILD_ARG $DETACH
fi

# Only show status if running in detached mode
if [ -n "$DETACH" ]; then
    echo ""
    echo "=========================================="
    echo "Services are starting up..."
    echo "=========================================="
    echo ""
    echo "Service URLs:"
    echo "  • Frontend:      http://localhost:3000"
    echo "  • Backend API:   http://localhost:8888"
    echo "  • API Docs:      http://localhost:8888/docs"
    echo "  • SAM Service:   http://localhost:8001"
    echo "  • MinIO Console: http://localhost:9001"
    echo "    (Login: minioadmin / minioadmin)"
    echo ""
    echo "Database:"
    echo "  • PostgreSQL:    localhost:5432"
    echo "  • Redis:         localhost:6379"
    echo ""
    echo "Useful commands:"
    echo "  ./start.sh --logs           # View all logs"
    echo "  ./start.sh --logs frontend  # View frontend logs"
    echo "  ./start.sh --status         # Check service status"
    echo "  ./start.sh --down           # Stop all services"
    echo ""
    echo "Waiting for services to become healthy..."
    sleep 5
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml ps
fi
