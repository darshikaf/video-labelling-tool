#!/bin/bash

echo "=== Medical Video Annotation Tool - Debug Script ==="
echo ""

echo "1. Checking Docker containers..."
docker-compose ps

echo ""
echo "2. Checking backend health..."
curl -s http://localhost:8000/health || echo "Backend not responding"

echo ""
echo "3. Checking backend API docs..."
curl -s http://localhost:8000/docs > /dev/null && echo "API docs accessible" || echo "API docs not accessible"

echo ""
echo "4. Testing backend registration endpoint..."
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}' \
  -w "\nHTTP Status: %{http_code}\n" || echo "Registration endpoint failed"

echo ""
echo "5. Checking database connection..."
docker-compose exec -T database psql -U postgres -d video_annotation -c "SELECT 1;" > /dev/null 2>&1 && echo "Database accessible" || echo "Database connection failed"

echo ""
echo "6. Checking backend logs (last 10 lines)..."
docker-compose logs --tail=10 backend

echo ""
echo "7. Checking frontend logs (last 10 lines)..."
docker-compose logs --tail=10 frontend

echo ""
echo "Debug complete. Check the output above for issues."