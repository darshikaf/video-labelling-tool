# Medical Video Annotation Tool

A modern web application for medical video annotation using SAM (Segment Anything Model) with interactive polygon editing capabilities.

## Architecture

- **Frontend**: React + TypeScript + Material-UI + Redux Toolkit
- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Object Storage**: MinIO (Development) / AWS S3 (Production) - for mask and binary data
- **SAM Service**: Ultralytics SAM + Redis caching
- **Deployment**: Docker + Docker Compose (Development) / EKS (Production)

### Hybrid Storage Architecture

- **PostgreSQL**: Metadata, relationships, SAM prompts, coordinates
- **MinIO/S3**: Binary files (PNG masks, video frames, extracted images)
- **Local Storage**: Original video files during processing

## Features

- Interactive video annotation with SAM integration
- Point and box prompts for mask generation
- Polygon editing for mask refinement
- Multi-class annotation support
- Export to COCO and YOLO formats
- User authentication and project management
- Real-time collaboration capabilities

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start

1. Clone and navigate to the project:
```bash
git clone <repository-url>
cd video-labelling-tool
```

2. Start all services:
```bash
./start.sh                    # Auto-detects platform
./start.sh --cpu              # Force CPU-only (Linux compatible)
./start.sh --gpu              # Force GPU mode (Apple Silicon/CUDA)
```

3. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8888
- SAM Service: http://localhost:8001
- API Documentation: http://localhost:8888/docs
- **MinIO Console**: http://localhost:9001 (admin interface)
- **MinIO API**: http://localhost:9000 (object storage)

### Manual Setup

1. Copy environment file:
```bash
cp .env.example .env
```

2. Start services individually:
```bash
# All services (Docker Compose v1)
docker-compose up --build

# All services (Docker Compose v2)
docker compose up --build

# Or specific services
docker-compose up --build frontend backend sam-service database redis minio
```

3. View logs:
```bash
# Docker Compose v1
docker-compose logs -f [service-name]

# Docker Compose v2
docker compose logs -f [service-name]
```

## Development Commands

### Backend (FastAPI)
```bash
# Run tests (use your Docker Compose command)
docker-compose exec backend python -m pytest
# or
docker compose exec backend python -m pytest

# Database migrations
docker-compose exec backend alembic upgrade head
# or
docker compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
# or
docker compose exec backend alembic revision --autogenerate -m "description"
```

### Frontend (React)
```bash
# Install dependencies
cd web-frontend && npm install

# Run tests
npm test

# Type checking
npm run typecheck

# Linting
npm run lint
```

### SAM Service
```bash
# Check model status
curl http://localhost:8001/health

# Test prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"image_data": "base64_image", "prompt_type": "point", "points": [{"x": 100, "y": 100, "is_positive": true}]}'
```

### MinIO Object Storage
```bash
# Access MinIO admin console
open http://localhost:9001
# Login: minioadmin / minioadmin

# Check MinIO health
curl http://localhost:9000/minio/health/live

# List buckets (using mc client)
docker run --rm --network host minio/mc ls minio
```

## Project Structure

```
video-labelling-tool/
├── web-frontend/              # React TypeScript frontend
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── pages/            # Page components
│   │   ├── store/            # Redux store and slices
│   │   ├── hooks/            # Custom React hooks
│   │   ├── utils/            # Utilities and API clients
│   │   └── types/            # TypeScript type definitions
├── web-backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Core functionality
│   │   ├── crud/             # Database operations
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── db/               # Database configuration
├── sam-service/              # Ultralytics SAM service
│   ├── core/                 # SAM prediction logic
│   └── schemas.py            # API schemas
├── k8s/                      # Kubernetes manifests
└── docker-compose.yml        # Development configuration
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user

### Projects
- `GET /api/v1/projects` - List user projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project details

### Videos
- `POST /api/v1/projects/{id}/videos` - Upload video
- `GET /api/v1/videos/{id}` - Get video details
- `GET /api/v1/videos/{id}/frames/{frame}` - Get video frame

### Annotations
- `GET /api/v1/frames/{id}/annotations` - Get frame annotations
- `POST /api/v1/frames/{id}/annotations` - Create annotation
- `PUT /api/v1/annotations/{id}` - Update annotation
- `GET /api/v1/annotations/{id}/mask-url` - Get presigned URL for mask

### SAM Service
- `POST /sam/predict` - Generate mask from prompts
- `GET /sam/health` - Service health check

## Database Schema

Core tables:
- `users` - User accounts
- `projects` - Annotation projects
- `videos` - Uploaded videos (metadata only)
- `frames` - Video frame references
- `categories` - Annotation categories
- `annotations` - Mask metadata + object storage keys (no binary data)

Object storage structure:
```
video-annotations/
├── projects/{id}/
│   └── videos/{id}/
│       └── frames/{num}/
│           └── annotations/{id}/
│               └── mask.png
```

## Deployment

### EKS Deployment

1. Build and push images:
```bash
# Build images
docker build -t your-registry/video-annotation-frontend:latest web-frontend
docker build -t your-registry/video-annotation-backend:latest web-backend
docker build -t your-registry/video-annotation-sam:latest sam-service

# Push to registry
docker push your-registry/video-annotation-frontend:latest
docker push your-registry/video-annotation-backend:latest
docker push your-registry/video-annotation-sam:latest
```

2. Deploy to Kubernetes:
```bash
kubectl apply -f k8s/
```

3. Configure services:
- Set up RDS for PostgreSQL
- Set up ElastiCache for Redis
- Set up S3 for object storage (replace MinIO)
- Configure ALB for load balancing
- Set up EFS for video storage

## Contributing

1. Follow the test-driven development approach
2. Maintain TypeScript types and comprehensive error handling
3. Write tests for new features (target >80% coverage)
4. Follow the existing code patterns and architecture
5. Update documentation for API changes

## Troubleshooting

### Common Issues

1. **SAM model download fails**: Check internet connection and disk space
2. **Database connection errors**: Ensure PostgreSQL is running and credentials are correct
3. **Redis connection fails**: Check Redis service status
4. **Video upload fails**: Check file permissions and upload directory exists
5. **MinIO connection fails**: Ensure MinIO service is running on ports 9000/9001
6. **Annotation mask not loading**: Check presigned URL expiration and MinIO bucket permissions

### MinIO Access & Configuration

**Admin Console Access:**
- URL: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`

**API Configuration:**
```bash
# Environment variables for backend
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=video-annotations
```

**Bucket Management:**
```bash
# Access MinIO console to:
# - View stored masks and files
# - Monitor storage usage
# - Configure bucket policies
# - Generate access keys for production
```

### Logs

View service logs:
```bash
# Docker Compose v1
docker-compose logs -f frontend
docker-compose logs -f backend
docker-compose logs -f sam-service

# Docker Compose v2
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f sam-service
```

### Reset Development Environment

```bash
# Docker Compose v1
docker-compose down -v

# Docker Compose v2
docker compose down -v

# Then continue with
docker system prune -f
./start.sh
```

## License

[License information here]
