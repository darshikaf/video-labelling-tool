# SAM 2 Implementation TODO List

## Overview

This document outlines the implementation tasks for migrating from SAM (frame-by-frame) to SAM 2 (video-based annotation with temporal propagation). Tasks are organized into **testable milestones** - each milestone produces a working, verifiable feature before moving to the next.

**Related Document**: See `VIDEO_ANNOTATION_ANALYSIS.md` for detailed analysis and architecture decisions.

---

## Milestone 1: SAM 2 Model Works Locally

**Goal**: Verify SAM 2 runs and produces masks on a single video
**Test**: Run script on sample video, confirm mask output

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Update `sam-service/requirements.txt` with SAM 2 dependencies | ✅ |
| 1.2 | Create basic SAM 2 predictor class (single video, single object) | ✅ |
| 1.3 | Write test script: load video → add point prompt → propagate → save masks | ✅ |

### ✅ Test Checkpoint
```bash
# Run test script locally, verify mask PNGs generated for all frames
python test_sam2_local.py --video sample.mp4 --output ./masks/
# Expected: masks/frame_0000.png, masks/frame_0001.png, ... created
```

---

## Milestone 2: SAM 2 API Endpoint (Single Object)

**Goal**: Call SAM 2 via HTTP, get propagated masks
**Test**: cURL/Postman request returns mask data

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Add `/initialize` endpoint (accepts video path/URL) | ✅ |
| 2.2 | Add `/add-object` endpoint (accepts frame index + points) | ✅ |
| 2.3 | Add `/propagate` endpoint (returns all frame masks) | ✅ |
| 2.4 | Update `sam-service/schemas.py` for new request/response formats | ✅ |

### ✅ Test Checkpoint
```bash
# Initialize session
curl -X POST http://localhost:8001/initialize \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/videos/sample.mp4"}'
# Expected: {"session_id": "abc123", "total_frames": 1800}

# Add object
curl -X POST http://localhost:8001/add-object \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "frame_idx": 0, "object_id": 1, "points": [[320, 240]], "labels": [1]}'
# Expected: {"object_id": 1, "mask": "base64..."}

# Propagate
curl -X POST http://localhost:8001/propagate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123"}'
# Expected: {"frames": [{"frame_idx": 0, "masks": {...}}, ...]}
```

---

## Milestone 3: Frontend Basic Integration ✅ COMPLETE

**Goal**: Click on video frame in UI → see propagated mask on all frames
**Test**: Manual UI test with sample video
**Completed**: December 2024

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Add "SAM 2 Mode" toggle to annotation page | ✅ |
| 3.2 | Implement "Initialize Session" button (calls backend) | ✅ |
| 3.3 | Implement click-to-add-object (single object for now) | ✅ |
| 3.4 | Implement "Propagate" button with loading state | ✅ |
| 3.5 | Display propagated masks on video player timeline | ✅ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Upload video to project
2. Open annotation page
3. Enable "SAM 2 Mode"
4. Click "Initialize Session" → should show "Session Active"
5. Click on an instrument in frame → should show initial mask
6. Click "Propagate" → should show progress bar
7. Scrub timeline → mask should appear on EVERY frame
```

### Implementation Details (December 2024)

**Files Created:**
- `web-frontend/src/components/annotation/SAM2Controls.tsx` - Main UI component
- `web-frontend/src/store/slices/sam2Slice.ts` - Redux state management

**Files Modified:**
- `web-frontend/src/pages/AnnotationPage.tsx` - Integrated SAM2Controls component
- `web-frontend/src/store/store.ts` - Added sam2 reducer
- `web-frontend/src/types/index.ts` - Added SAM2 TypeScript interfaces
- `web-frontend/src/utils/api.ts` - Added SAM2 API client functions

**Key Features Implemented:**
1. **SAM2Controls Component**: Toggle switch, session management, object list, propagation controls
2. **Redux State**: Full state management for sessions, objects, masks, and UI state
3. **API Integration**: Initialize, add-object, propagate, refine, close session endpoints
4. **Progress Tracking**: Real-time propagation progress with percentage display
5. **Object Visualization**: Color-coded object list with frame counts

**API Endpoints Used:**
- `POST /sam2/initialize` - Start a new video session
- `POST /sam2/add-object` - Add an object with click points
- `POST /sam2/propagate` - Propagate masks to all frames
- `POST /sam2/refine` - Refine mask on specific frame
- `POST /sam2/session/{id}/close` - Clean up session

---

## Milestone 4: Session Management

**Goal**: Multiple users can annotate simultaneously without conflicts
**Test**: Open two browser tabs, annotate different videos concurrently

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Add Redis for session state storage | ⬜ |
| 4.2 | Implement session ID generation and tracking | ⬜ |
| 4.3 | Add session timeout (cleanup after 30 min idle) | ⬜ |
| 4.4 | Add session status endpoint (`/session/{id}/status`) | ⬜ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Open Browser Tab A → annotate Video 1
2. Open Browser Tab B → annotate Video 2
3. Both sessions should work independently
4. Verify: Tab A actions don't affect Tab B results
5. Leave Tab A idle for 30+ minutes → session should expire
```

---

## Milestone 5: Refinement & Multi-Frame Editing

**Goal**: Correct mask on a specific frame, re-propagate
**Test**: Mask drifts on frame 50 → add refinement click → mask corrects

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Add `/refine` endpoint (add points to specific frame) | ⬜ |
| 5.2 | Frontend: click on any frame to add refinement point | ⬜ |
| 5.3 | Re-propagate from refinement point (forward and/or backward) | ⬜ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Complete initial propagation (Milestone 3)
2. Navigate to a frame where mask has drifted/is incorrect
3. Click to add refinement point (positive or negative)
4. Observe mask update on that frame
5. Click "Re-propagate" → correction should flow to subsequent frames
```

---

## Milestone 6: Multi-Object Tracking

**Goal**: Track multiple objects (e.g., forceps + tissue) in same video
**Test**: Add two objects, each gets separate mask across all frames

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Support multiple object IDs in predictor | ⬜ |
| 6.2 | Add object list panel in frontend | ⬜ |
| 6.3 | Per-object category assignment | ⬜ |
| 6.4 | Visual distinction (different colors per object) | ⬜ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Initialize session on surgical video
2. Click "Add Object" → name it "Forceps" → assign to "Instrument" category
3. Click on forceps in frame → propagate
4. Click "Add Object" → name it "Tissue" → assign to "Anatomy" category
5. Click on tissue in frame → propagate
6. Scrub timeline → both objects should have separate masks
7. Verify: Forceps = red, Tissue = blue (different colors)
```

---

## Milestone 7: Save Annotations to Database

**Goal**: Propagated masks persist to database for export
**Test**: Save annotations → refresh page → annotations still visible

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Create bulk save endpoint (all frames, all objects) | ⬜ |
| 7.2 | Update database schema for tracked objects | ⬜ |
| 7.3 | Frontend "Save All" button | ⬜ |
| 7.4 | Load existing annotations when reopening video | ⬜ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Complete multi-object annotation (Milestone 6)
2. Click "Save All" → should show success message
3. Close browser tab completely
4. Reopen annotation page for same video
5. All masks should be loaded and visible
6. Verify: Export still works with saved annotations
```

---

## Milestone 8: Cloud GPU Deployment

**Goal**: SAM 2 service runs on cloud GPU, accessible from web app
**Test**: Full workflow works with cloud-hosted SAM 2

| Task | Description | Status |
|------|-------------|--------|
| 8.1 | Choose cloud provider (Modal / Replicate / AWS) | ⬜ |
| 8.2 | Deploy SAM 2 service to cloud GPU | ⬜ |
| 8.3 | Update web-backend to call cloud SAM 2 service | ⬜ |
| 8.4 | Test latency (< 500ms per interaction) | ⬜ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Ensure local SAM 2 service is STOPPED
2. Configure web-backend to use cloud SAM 2 URL
3. Complete full annotation workflow (add object → propagate → refine → save)
4. Measure latency:
   - Initialize: should be < 5 seconds
   - Add object: should be < 500ms
   - Propagate (1 hour video): should be < 60 seconds
5. Verify: Results identical to local testing
```

---

## Milestone 9: Load Testing & Production

**Goal**: System handles 10 concurrent users reliably
**Test**: Simulate 10 users annotating simultaneously

| Task | Description | Status |
|------|-------------|--------|
| 9.1 | Set up auto-scaling for GPU instances | ⬜ |
| 9.2 | Add request queuing for burst handling | ⬜ |
| 9.3 | Run load test with 10 concurrent sessions | ⬜ |
| 9.4 | Monitor and optimize as needed | ⬜ |
| 9.5 | Deploy to production | ⬜ |

### ✅ Test Checkpoint
```bash
# Run load test script
python load_test.py --users 10 --duration 30m

# Expected results:
# - All 10 users complete annotation sessions
# - No session conflicts or data corruption
# - Average latency remains < 1 second
# - No OOM errors or GPU crashes
# - Queue handles burst requests gracefully
```

---

## Summary

| Milestone | Description | Tasks | Test Type |
|-----------|-------------|-------|-----------|
| 1 | SAM 2 model works locally | 3 | Script |
| 2 | API returns masks | 4 | cURL/Postman |
| 3 | UI shows propagated masks | 5 | Manual UI |
| 4 | Multi-user sessions | 4 | Manual (2 tabs) |
| 5 | Refinement works | 3 | Manual UI |
| 6 | Multi-object tracking | 4 | Manual UI |
| 7 | Annotations persist | 4 | Manual UI |
| 8 | Cloud GPU works | 4 | Manual + Latency |
| 9 | 10 concurrent users | 5 | Load test script |

**Total: 9 milestones, 36 tasks**

---

## Progress Tracking

### Current Status
- **Current Milestone**: Milestone 4 (Session Management)
- **Completed Milestones**: 3/9
- **Completed Tasks**: 15/36

### Milestone Completion Log
| Milestone | Completed Date | Notes |
|-----------|---------------|-------|
| 1 | Dec 2024 | SAM 2 model loads, test script generates masks in simulation mode |
| 2 | Dec 2024 | API endpoints working, tested with real video (1732 frames) |
| 3 | Dec 2024 | Frontend integration with SAM2Controls component, Redux state, click-to-track |
| 4 | In Progress | Basic session management exists, Redis integration pending |
| 5 | - | - |
| 6 | - | - |
| 7 | - | - |
| 8 | - | - |
| 9 | - | - |

### Implementation Notes (Dec 2024)
- Using `uv` for dependency management instead of pip
- SAM 2 requires JPEG folder input, so videos are extracted to temp directories
- Supports any video format (MOV, MP4, etc.) via OpenCV frame extraction
- Running on CPU is slow (~1 frame/sec for propagation); GPU recommended for production
- Added `/add-object-box`, `/refine`, `/frame-masks`, `/session/{id}` endpoints

---

## Getting Started for New Developers

### Frontend SAM2 Integration

The SAM2 frontend integration consists of:

```
web-frontend/src/
├── components/annotation/
│   └── SAM2Controls.tsx       # Main UI component
├── store/slices/
│   └── sam2Slice.ts           # Redux state & async thunks
├── types/
│   └── index.ts               # SAM2 TypeScript interfaces
└── utils/
    └── api.ts                 # sam2API client
```

### Key State Structure (Redux)

```typescript
interface SAM2State {
  isEnabled: boolean              // SAM2 mode toggle
  session: SAM2Session | null     // Active session info
  objects: SAM2TrackedObject[]    // List of tracked objects
  frameMasks: Record<number, Record<number, string>>  // frameIdx -> objectId -> mask
  isPropagating: boolean          // Propagation in progress
  propagationProgress: number     // 0-100%
}
```

### User Workflow

1. User enables "SAM 2 Mode" toggle
2. User clicks "Initialize Session" (loads video into SAM2 backend)
3. User clicks on canvas to add objects (left-click = include, right-click = exclude)
4. Backend returns initial mask for clicked frame
5. User clicks "Propagate to All Frames"
6. Masks are generated for all video frames
7. User can scrub timeline to see masks on each frame

### Backend Endpoints Required

The frontend expects these SAM2 service endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sam2/initialize` | POST | Start video session |
| `/sam2/add-object` | POST | Add object with points |
| `/sam2/propagate` | POST | Propagate to all frames |
| `/sam2/refine` | POST | Refine mask on frame |
| `/sam2/session/{id}/close` | POST | Cleanup session |

### Next Steps for Developers

1. **Milestone 4**: Add Redis for proper session state management
2. **Milestone 5**: Implement refinement UI (click on any frame to correct mask)
3. **Milestone 6**: Add multi-object tracking UI (object list management)
4. **Milestone 7**: Implement "Save All" to persist annotations to database

---

*Document Version: 1.2*
*Created: December 2024*
*Updated: December 2024*
