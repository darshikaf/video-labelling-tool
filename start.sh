#!/bin/bash

echo "Starting Medical Video Annotation Tool Development Environment..."

# Create uploads directory
mkdir -p uploads

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
fi

# Start services
echo "Starting Docker Compose services..."
docker-compose up --build -d

echo ""
echo "Services starting up..."
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- SAM Service: http://localhost:8001"
echo "- Database: localhost:5432"
echo "- Redis: localhost:6379"
echo "- MinIO: http://localhost:9000"
echo ""
echo "To view logs: docker-compose logs -f [service-name]"
echo "To stop: docker-compose down"