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

## Milestone 5: Mask Refinement & Polygon Editing

**Goal**: Refine mask boundaries before and after propagation using both click-based and polygon editing methods
**Test**: Edit polygon boundary on initial mask → propagate with refined mask → correct drifted masks on later frames

### Part A: Pre-Propagation Polygon Editing

Allow users to manually edit the mask boundary using draggable polygon nodes **before** propagation starts.

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Add "Edit Boundary" button in SAM2Controls (appears after initial mask) | ⬜ |
| 5.2 | Integrate PolygonEditor component with SAM2 workflow | ⬜ |
| 5.3 | Show polygon overlay with draggable nodes on mask boundary | ⬜ |
| 5.4 | Convert edited polygon back to mask for propagation | ⬜ |
| 5.5 | Update SAM2 state to use refined mask instead of original | ⬜ |

**Existing Components:**
- `PolygonEditor.tsx` - Already has mask-to-polygon conversion, node dragging, polygon-to-mask conversion
- Needs integration with SAM2Controls and state management

### Part B: Click-Based Refinement (Post-Propagation)

Allow users to add positive/negative clicks to correct drifted masks on any frame.

| Task | Description | Status |
|------|-------------|--------|
| 5.6 | Expose `/refine` endpoint in UI (backend already exists) | ⬜ |
| 5.7 | Frontend: click on any frame to add refinement point | ⬜ |
| 5.8 | Re-propagate from refinement point (forward and/or backward) | ⬜ |

**Existing Components:**
- `refineSAM2Mask` Redux thunk - Already implemented
- `/refine` API endpoint - Already exists in SAM service
- Needs UI buttons and click handling on propagated frames

### ✅ Test Checkpoint - Part A (Polygon Editing)
```
Manual Test Steps:
1. Initialize SAM2 session on video
2. Click on object → initial mask appears
3. Click "Edit Boundary" button
4. Polygon overlay appears with draggable nodes on mask boundary
5. Drag nodes to adjust the boundary (e.g., include missed area, exclude over-segmented area)
6. Click "Done Editing" → refined mask replaces original
7. Click "Propagate" → propagation uses the refined mask
8. Verify: Propagated masks follow the refined boundary, not the original
```

### ✅ Test Checkpoint - Part B (Click Refinement)
```
Manual Test Steps:
1. Complete initial propagation (Milestone 3)
2. Navigate to a frame where mask has drifted/is incorrect
3. Click to add refinement point (positive or negative)
4. Observe mask update on that frame
5. Click "Re-propagate" → correction should flow to subsequent frames
```

### Implementation Notes

**Polygon Editing Workflow:**
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Initial Click  │ ──▶ │  SAM2 Mask      │ ──▶ │  Edit Boundary  │
│  on Object      │     │  Generated      │     │  (Optional)     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              ▼
                        │   Propagate     │ ◀── ┌─────────────────┐
                        │   to All Frames │     │  Refined Mask   │
                        └─────────────────┘     │  (Polygon Edit) │
                                                └─────────────────┘
```

**Key Integration Points:**
- SAM2Controls: Add "Edit Boundary" button (visible when mask exists, before propagation)
- AnnotationPage: Mount PolygonEditor overlay when editing mode is active
- sam2Slice: Add `isEditingMask` state and action to update mask from polygon edit

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

## Milestone 7: Save Annotations to Database ✅ COMPLETE

**Goal**: Propagated masks persist to database for export
**Test**: Save annotations → export works correctly
**Completed**: December 2024

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Create bulk save endpoint (all frames, all objects) | ✅ |
| 7.2 | Update database schema for tracked objects | ✅ (uses existing Annotation table) |
| 7.3 | Frontend "Save All" button | ✅ |
| 7.4 | Load existing annotations when reopening video | ⬜ (future enhancement) |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Complete SAM2 propagation (Milestone 3)
2. Click "Save All to Database" → should show progress bar
3. Wait for save to complete (shows "Saved to database")
4. Open Export dialog → select YOLO or COCO format
5. Export should now contain all propagated masks!
```

### Implementation Details (December 2024)

**Files Modified:**
- `web-frontend/src/store/slices/sam2Slice.ts` - Added `saveSAM2MasksToDatabase` async thunk
- `web-frontend/src/components/annotation/SAM2Controls.tsx` - Added "Save All to Database" button
- `web-frontend/src/utils/api.ts` - Added `annotationAPI.saveSAM2Masks()` batch save function
- `web-backend/app/services/export_service.py` - Fixed YOLO export contour extraction bug

**How It Works:**
1. User clicks "Save All to Database" button
2. Frontend iterates through all `frameMasks` (frameIdx → objectId → base64 mask)
3. For each mask, calls `POST /api/v1/videos/{video_id}/frames/{frame_number}/annotations`
4. Progress is shown in real-time
5. Masks are stored in PostgreSQL (metadata) and MinIO (mask PNG files)
6. Export service queries annotations and fetches mask data from MinIO
7. Masks are converted to polygons using OpenCV contour extraction
8. YOLO/COCO format files are generated with proper polygon coordinates

**Bugs Fixed (Dec 26, 2024):**
- **YOLO Export Empty Files**: Contour extraction code was incorrectly placed in `else` block (only ran when mask was None). Moved to run when mask IS successfully decoded.
- **422 Validation Errors**: Removed `null` values from API payload for optional fields, added validation to skip empty mask data.

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

## Milestone 10: Category Management

**Goal**: Users can customize annotation categories for their specific use case (e.g., surgical tools, anatomy)
**Test**: Create custom categories, assign to objects, export with correct labels

| Task | Description | Status |
|------|-------------|--------|
| 10.1 | Category CRUD API (create, read, update, delete categories) | ⬜ |
| 10.2 | Category management UI in project settings | ⬜ |
| 10.3 | Custom color picker for each category | ⬜ |
| 10.4 | Category presets (Surgical Tools, Anatomy, General) | ⬜ |
| 10.5 | Import/export category lists (JSON/CSV) | ⬜ |
| 10.6 | Category selector in SAM2 object creation flow | ⬜ |

### ✅ Test Checkpoint
```
Manual Test Steps:
1. Open project settings
2. Navigate to "Categories" tab
3. Delete default categories (Person, Anatomy, etc.)
4. Add custom categories:
   - "Forceps" with color #FF6B6B
   - "Scissors" with color #4ECDC4
   - "Gallbladder" with color #45B7D1
5. Save changes
6. Open annotation page → enable SAM 2 Mode
7. When adding object, select category from dropdown
8. Export to YOLO → verify classes.txt has custom category names
```

### Suggested Category Presets

**Surgical Instruments:**
- Forceps, Scissors, Grasper, Needle Driver, Retractor, Clip Applier, Suction, Cautery

**Anatomy (Laparoscopic):**
- Liver, Gallbladder, Stomach, Intestine, Peritoneum, Blood Vessel, Fat, Connective Tissue

**General Objects:**
- Person, Vehicle, Animal, Tool, Container, Furniture

---

## Summary

| Milestone | Description | Tasks | Test Type | Status |
|-----------|-------------|-------|-----------|--------|
| 1 | SAM 2 model works locally | 3 | Script | ✅ Complete |
| 2 | API returns masks | 4 | cURL/Postman | ✅ Complete |
| 3 | UI shows propagated masks | 5 | Manual UI | ✅ Complete |
| 4 | Multi-user sessions | 4 | Manual (2 tabs) | 🟡 Partial |
| 5 | Mask refinement & polygon editing | 8 | Manual UI | ⬜ Not started |
| 6 | Multi-object tracking | 4 | Manual UI | ⬜ Not started |
| 7 | Annotations persist | 4 | Manual UI | ✅ Complete |
| 8 | Cloud GPU works | 4 | Manual + Latency | ⬜ Not started |
| 9 | 10 concurrent users | 5 | Load test script | ⬜ Not started |
| 10 | Category management | 6 | Manual UI | ⬜ Not started |

**Total: 10 milestones, 47 tasks**
**Completed: 4 milestones (1, 2, 3, 7)**

---

## Progress Tracking

### Current Status
- **Current Milestone**: Milestone 5 (Mask Refinement & Polygon Editing) or Milestone 10 (Category Management)
- **Completed Milestones**: 4/10 (1, 2, 3, 7)
- **Completed Tasks**: 19/47
- **Last Updated**: December 26, 2024

### Milestone Completion Log
| Milestone | Completed Date | Notes |
|-----------|---------------|-------|
| 1 | Dec 2024 | SAM 2 model loads, test script generates masks in simulation mode |
| 2 | Dec 2024 | API endpoints working, tested with real video (1732 frames) |
| 3 | Dec 2024 | Frontend integration with SAM2Controls component, Redux state, click-to-track |
| 4 | Partial | Basic session management exists, Redis integration pending |
| 5 | - | Polygon editing + click refinement - PolygonEditor component exists, needs SAM2 integration |
| 6 | - | Multi-object UI not started |
| 7 | Dec 26, 2024 | **Save All to Database** - batch save masks + YOLO/COCO export fully working |
| 8 | - | Cloud GPU deployment not started |
| 9 | - | Load testing not started |
| 10 | - | Category management not started |

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

*Document Version: 1.6*
*Created: December 2024*
*Updated: December 26, 2024*
*Last Change: Expanded Milestone 5 - Added polygon boundary editing before propagation + click-based refinement*
