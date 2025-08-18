#!/bin/bash

echo "Starting Medical Video Annotation Tool Development Environment..."

# Function to detect Docker Compose command
get_docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo "Error: Neither 'docker-compose' nor 'docker compose' is available" >&2
        exit 1
    fi
}

# Get the appropriate Docker Compose command
DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
echo "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Create uploads directory
mkdir -p uploads

# Copy environment file  
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
fi

# Detect platform and start appropriate services
PLATFORM=$(uname -m)
if [[ "$1" == "--cpu" ]] || [[ "$PLATFORM" == "x86_64" && "$1" != "--gpu" ]]; then
    echo "Starting with CPU-only configuration (Linux compatible)..."
    $DOCKER_COMPOSE_CMD -f docker-compose.yml -f docker-compose.cpu.yml up --build -d
else
    echo "Starting with GPU support (Apple Silicon/CUDA)..."
    $DOCKER_COMPOSE_CMD up --build -d
fi

echo ""
echo "Services starting up..."
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- SAM Service: http://localhost:8001"
echo "- Database: localhost:5432"
echo "- Redis: localhost:6379"
echo "- MinIO: http://localhost:9000"
echo ""
echo "Usage options:"
echo "  ./start.sh          - Auto-detect platform (CPU for x86_64 Linux, GPU for others)"
echo "  ./start.sh --cpu    - Force CPU-only mode"
echo "  ./start.sh --gpu    - Force GPU mode"
echo ""
echo "To view logs: $DOCKER_COMPOSE_CMD logs -f [service-name]"
echo "To stop: $DOCKER_COMPOSE_CMD down"