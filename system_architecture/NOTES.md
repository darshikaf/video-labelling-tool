# Video Annotation Tool with SAM 2

This document outlines the architecture and implementation status of the video annotation tool leveraging Meta's SAM 2 (Segment Anything Model 2) for video-based segmentation.

**Last Updated:** December 2024

---

## Current Implementation Status

### ✅ Completed

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend UI | React + TypeScript + Vite | ✅ Implemented |
| State Management | Redux Toolkit | ✅ Implemented |
| SAM 2 Controls | SAM2Controls.tsx + sam2Slice.ts | ✅ Implemented |
| Web Backend | FastAPI (Python) | ✅ Implemented |
| SAM 2 Service | FastAPI + SAM 2 Model | ✅ Implemented |
| Database | PostgreSQL | ✅ Implemented |
| File Storage | MinIO | ✅ Implemented |
| Docker Setup | docker-compose.yml | ✅ Implemented |

### 🟡 In Progress

| Component | Status |
|-----------|--------|
| Redis Session Management | Partial - basic sessions work |
| Mask Refinement UI | API ready, UI pending |
| Multi-Object Tracking UI | Basic implementation |

### ⬜ Not Started

| Component | Notes |
|-----------|-------|
| Cloud GPU Deployment | Need to select provider (Modal/Replicate/AWS) |
| Save Annotations to DB | Propagated masks need persistence |
| Batch Export | Export all annotations at once |

---

## System Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Browser                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    React Frontend (:3000)                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │  │
│  │  │ VideoPlayer │ │AnnotCanvas  │ │    SAM2Controls         │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘ │  │
│  │                          │                    │                │  │
│  │                    Redux Store (sam2Slice, annotationSlice)   │  │
│  └──────────────────────────┼────────────────────┼───────────────┘  │
│                              │                    │                  │
└──────────────────────────────┼────────────────────┼──────────────────┘
                               │                    │
                    ┌──────────▼──────────┐  ┌──────▼──────────┐
                    │  Web Backend (:8000) │  │ SAM 2 (:8002)   │
                    │  - Auth              │  │ - Initialize    │
                    │  - Videos            │  │ - Add Object    │
                    │  - Annotations       │  │ - Propagate     │
                    │  - Export            │  │ - Refine        │
                    └──────────┬───────────┘  └────────┬────────┘
                               │                       │
                    ┌──────────▼───────────────────────▼────────┐
                    │              Data Layer                    │
                    │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
                    │  │PostgreSQL│ │  MinIO  │ │  Redis  │      │
                    │  └─────────┘ └─────────┘ └─────────┘      │
                    └───────────────────────────────────────────┘
```

### Services

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| web-frontend | 3000 | React + Vite | User interface |
| web-backend | 8000 | FastAPI | API, auth, database |
| sam-service | 8002 | FastAPI + SAM 2 | Video segmentation |
| postgres | 5432 | PostgreSQL | Relational data |
| redis | 6379 | Redis | Sessions, cache |
| minio | 9000 | MinIO | File storage |

---

## Frontend Architecture

### Key Components

```
web-frontend/src/
├── components/
│   └── annotation/
│       ├── SAM2Controls.tsx      # SAM 2 mode UI
│       ├── AnnotationCanvas.tsx  # Drawing canvas
│       ├── VideoPlayer.tsx       # Video playback
│       └── PolygonEditor.tsx     # Manual editing
├── store/
│   └── slices/
│       ├── sam2Slice.ts          # SAM 2 state
│       ├── annotationSlice.ts    # Annotations
│       └── videoSlice.ts         # Video state
├── pages/
│   ├── AnnotationPage.tsx        # Main annotation view
│   ├── DashboardPage.tsx         # Project list
│   └── ProjectPage.tsx           # Single project
└── utils/
    └── api.ts                    # API clients
```

### SAM 2 Redux State

```typescript
interface SAM2State {
  isEnabled: boolean                    // SAM 2 mode toggle
  session: SAM2Session | null           // Active session
  objects: SAM2TrackedObject[]          // Tracked objects
  frameMasks: Record<number, Record<number, string>>  // Masks per frame
  isPropagating: boolean                // Propagation status
  propagationProgress: number           // 0-100%
}
```

### User Workflow

1. **Enable SAM 2 Mode** - Toggle switch in UI
2. **Initialize Session** - Load video into SAM 2 backend
3. **Click to Add Object** - Left-click includes, right-click excludes
4. **View Initial Mask** - Mask appears on clicked frame
5. **Propagate** - Generate masks for all frames
6. **Review** - Scrub timeline to check masks
7. **Refine** (coming soon) - Click on any frame to correct

---

## SAM 2 Service Architecture

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sam2/initialize` | POST | Start video session |
| `/sam2/add-object` | POST | Add object with points |
| `/sam2/add-object-box` | POST | Add object with bounding box |
| `/sam2/propagate` | POST | Propagate to all frames |
| `/sam2/refine` | POST | Refine mask on frame |
| `/sam2/frame-masks/{session_id}/{frame_idx}` | GET | Get masks for frame |
| `/sam2/session/{session_id}` | GET | Get session status |
| `/sam2/session/{session_id}/close` | POST | Close session |
| `/health` | GET | Service health check |
| `/cleanup` | POST | Force cleanup expired sessions |

### Resource Limits

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `MAX_CONCURRENT_SESSIONS` | 2 | Prevent memory exhaustion |
| `MAX_VIDEO_FRAMES` | 300 | ~10 seconds at 30fps |
| `MAX_FRAME_DIMENSION` | 1920 | Full HD max |
| `SESSION_TIMEOUT` | 300s | Auto-cleanup idle sessions |

### Model Options

| Model | Size | Speed | Use Case |
|-------|------|-------|----------|
| `tiny` | 38MB | Very Fast | Development |
| `small` | 181MB | Fast | Light production |
| `base_plus` | 375MB | Medium | Production |
| `large` | 814MB | Slow | High accuracy |

---

## Development Setup

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker logs sam-service -f

# Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# SAM 2 API: http://localhost:8002/docs
```

### Local Development

```bash
# Frontend
cd web-frontend
npm install
npm run dev

# SAM 2 Service
cd sam-service
uv sync
uv run uvicorn main:app --reload --port 8002
```

---

## Directory Structure (Actual)

```
video-labelling-tool/
├── web-frontend/              # React + TypeScript frontend
│   ├── src/
│   │   ├── components/        # UI components
│   │   ├── pages/            # Page components
│   │   ├── store/            # Redux store
│   │   ├── types/            # TypeScript types
│   │   └── utils/            # Utilities
│   ├── package.json
│   └── vite.config.ts
├── web-backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── core/             # Core logic
│   │   ├── crud/             # Database operations
│   │   ├── models/           # SQLAlchemy models
│   │   └── schemas/          # Pydantic schemas
│   └── pyproject.toml
├── sam-service/               # SAM 2 video service
│   ├── core/
│   │   └── sam2_video_predictor.py
│   ├── main.py               # FastAPI app
│   ├── schemas.py            # Request/response schemas
│   └── pyproject.toml
├── docs/                      # Documentation
│   ├── SAM2_IMPLEMENTATION_TODO.md
│   ├── VIDEO_ANNOTATION_ANALYSIS.md
│   ├── RESOURCE_MANAGEMENT.md
│   └── QUICK_START.md
├── system_architecture/       # Architecture docs
├── docker-compose.yml         # Docker services
└── README.md
```

---

## Key Technical Decisions

### 1. SAM 2 over SAM 1

**Reason:** SAM 2 provides native video support with temporal consistency. SAM 1 required frame-by-frame annotation.

**Impact:** 10-50x reduction in annotation time.

### 2. Separate SAM 2 Service

**Reason:** SAM 2 requires significant GPU/CPU resources. Isolating it allows independent scaling.

**Impact:** Can scale SAM 2 instances separately from web backend.

### 3. Redux for SAM 2 State

**Reason:** Complex async operations (initialize, add object, propagate) with progress tracking.

**Impact:** Clean state management with Redux Toolkit's createAsyncThunk.

### 4. Base64 Masks over URLs

**Reason:** Simplifies mask transfer between services. No need for temporary file storage.

**Tradeoff:** Larger payloads, but acceptable for ~300 frame videos.

### 5. Session-Based API

**Reason:** SAM 2 maintains internal state (video frames, object memory) that must persist across requests.

**Impact:** Need session management and cleanup.

---

## Next Steps

See `docs/SAM2_IMPLEMENTATION_TODO.md` for detailed task tracking.

### Priority Order

1. **Milestone 4:** Redis session management
2. **Milestone 5:** Refinement UI
3. **Milestone 6:** Multi-object tracking UI
4. **Milestone 7:** Save annotations to database
5. **Milestone 8:** Cloud GPU deployment

---

*Document Version: 2.0*
*Created: 2024*
*Updated: December 2024*
