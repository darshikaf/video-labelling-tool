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
OS=$(uname -s)

# Set TARGETPLATFORM environment variable for Docker builds
if [[ "$PLATFORM" == "arm64" ]] && [[ "$OS" == "Darwin" ]]; then
    export TARGETPLATFORM="linux/arm64"
    PLATFORM_NAME="Apple Silicon (ARM64)"
elif [[ "$PLATFORM" == "x86_64" ]] && [[ "$OS" == "Linux" ]]; then
    export TARGETPLATFORM="linux/amd64"
    PLATFORM_NAME="Linux x86_64"
elif [[ "$PLATFORM" == "aarch64" ]] && [[ "$OS" == "Linux" ]]; then
    export TARGETPLATFORM="linux/arm64"
    PLATFORM_NAME="Linux ARM64"
else
    export TARGETPLATFORM="linux/amd64"
    PLATFORM_NAME="Default (AMD64)"
fi

echo "Detected platform: $PLATFORM_NAME"
echo "Using Docker target platform: $TARGETPLATFORM"

# Choose configuration based on arguments and platform
if [[ "$1" == "--cpu" ]]; then
    echo "Starting with CPU-only configuration (forced)..."
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml -f docker-compose.cpu.yml up --build -d
elif [[ "$1" == "--gpu" ]]; then
    echo "Starting with GPU support (forced)..."
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml up --build -d
elif [[ "$PLATFORM" == "x86_64" && "$OS" == "Linux" ]]; then
    echo "Starting with CPU-only configuration (Linux x86_64 detected)..."
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml -f docker-compose.cpu.yml up --build -d
else
    echo "Starting with multi-platform configuration..."
    $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml up --build -d
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
echo "  ./start.sh          - Auto-detect platform (CPU for Linux x86_64, multi-platform for others)"
echo "  ./start.sh --cpu    - Force CPU-only mode (Linux compatible)"
echo "  ./start.sh --gpu    - Force GPU mode (requires GPU support)"
echo ""
echo "Platform compatibility:"
echo "  - Linux x86_64: Uses CPU-only configuration by default"
echo "  - Linux ARM64: Uses multi-platform configuration"
echo "  - macOS Apple Silicon: Uses multi-platform configuration"
echo ""
echo "To view logs: $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml logs -f [service-name]"
echo "To stop: $DOCKER_COMPOSE_CMD -f docker-compose.linux.yml down"
