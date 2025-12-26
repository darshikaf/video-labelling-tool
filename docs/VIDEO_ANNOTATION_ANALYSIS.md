# Video Annotation Tool: Analysis & Migration Plan

## Executive Summary

This document analyzes our current video annotation approach and evaluates state-of-the-art alternatives for annotating medical procedure videos. The primary goal is to achieve **temporal stability** in annotations, which is critical for training downstream segmentation models.

---

## 1. Current State Analysis

### 1.1 Current Architecture

| Component | Implementation |
|-----------|---------------|
| Segmentation Model | SAM (Segment Anything Model) - image-based |
| Annotation Workflow | Frame-by-frame (each frame annotated independently) |
| Prompt Types | Point clicks + bounding boxes |
| Temporal Propagation | None |
| Object Tracking | None |
| Mask Refinement | Polygon editor available |
| Coordinate System | Standardized 640x480 |

### 1.2 Current Workflow

```
User Workflow (Frame-by-Frame):
├── Navigate to Frame 1 → Click points → SAM generates mask → Save
├── Navigate to Frame 2 → Click points → SAM generates mask → Save
├── Navigate to Frame 3 → Click points → SAM generates mask → Save
└── ... (repeat for every single frame)
```

### 1.3 Critical Limitations

| Issue | Impact on Medical Video Annotation |
|-------|-----------------------------------|
| **No temporal propagation** | Must re-annotate every frame manually |
| **No object tracking** | Same instrument must be identified repeatedly |
| **Temporal inconsistency** | Mask boundaries jitter between frames |
| **Time-intensive** | 1-hour video at 30fps = 108,000 frames to annotate |
| **Poor training data quality** | Jittery masks produce poor segmentation models |

### 1.4 Why This Matters for Medical Procedures

Medical procedure videos have specific characteristics that make frame-by-frame annotation particularly problematic:

- **Long duration**: Surgeries can last 2-6 hours
- **Slow object movement**: Instruments and anatomy move gradually between frames
- **Multiple persistent objects**: Same instruments appear throughout procedure
- **Occlusions**: Instruments go behind tissue and reappear
- **Fine detail requirements**: Small instrument tips need precise segmentation

---

## 2. Available Solutions

### 2.1 Solution Comparison Matrix

| Model | Type | Temporal Consistency | Long Video Support | Speed | Medical Suitability |
|-------|------|---------------------|-------------------|-------|---------------------|
| **SAM** (current) | Image | ❌ None | ❌ N/A | Fast | Low |
| **SAM 2** | Video | ✅ Excellent | ✅ Good | ~30 FPS | High |
| **Cutie** | Video | ✅ Excellent | ✅ Excellent | ~50 FPS | Very High |
| **XMem** | Video | ✅ Very Good | ✅ Excellent | ~30 FPS | High |
| **DEVA** | Video | ✅ Good | ✅ Good | ~25 FPS | Medium-High |

### 2.2 SAM 2 (Segment Anything Model 2)

**Release**: Meta AI, July 2024

**Key Capabilities**:
- Unified architecture for both image and video segmentation
- Memory mechanism that tracks objects across frames
- Streaming inference for real-time processing
- Promptable interface (points, boxes, masks)
- Bidirectional propagation (forward and backward in time)
- Multi-object tracking with separate object IDs

**Workflow Change**:
```
Proposed Workflow (SAM 2):
├── Load video into SAM 2 session
├── Navigate to Frame 1 → Click on "Forceps" → Mask auto-propagates to ALL frames
├── Navigate to Frame 50 (only if mask drifted) → Add refinement click
├── Add second object "Tissue" → Auto-propagates
└── Export all annotations for all frames
```

**Efficiency Gain**:
| Metric | Current (SAM) | With SAM 2 |
|--------|--------------|------------|
| Clicks per 100 frames | 100+ | 1-5 |
| Annotation time (1-hour video) | Days | Hours |
| Temporal consistency | Poor | Excellent |

### 2.3 Cutie

**Release**: CVPR 2024 ("Putting the Object Back into Video Object Segmentation")

**Key Differentiators from SAM 2**:
- Object-centric memory (remembers each object as distinct entity)
- More efficient for very long videos
- Better separation of overlapping objects
- Lighter memory footprint
- Faster inference (~50 FPS vs ~30 FPS)

**Particularly Strong For**:
- Multi-hour surgical procedures
- Scenes with many overlapping instruments
- Resource-constrained environments

### 2.4 XMem

**Release**: ECCV 2022 ("Long-Term Video Object Segmentation with an Atkinson-Shiffrin Memory Model")

**Unique Architecture**:
- Three-tier memory system mimicking human memory:
  - Sensory memory (immediate frames)
  - Working memory (recent context)
  - Long-term memory (persistent objects)

**Best For**:
- Very long videos (2+ hours)
- Objects that leave frame and return later
- Preventing long-term drift

### 2.5 DEVA

**Release**: ICCV 2023 ("Tracking Anything with Decoupled Video Segmentation")

**Key Innovation**:
- Decouples segmentation from tracking
- Can use ANY image segmenter with ANY tracker
- Highly flexible architecture

**Potential Configuration**:
- Use MedSAM (medical-tuned) for segmentation
- Use DEVA's tracking for temporal propagation
- Best of both worlds: medical accuracy + temporal consistency

---

## 3. Medical-Specific Considerations

### 3.1 Available Medical Models

| Model | Training Data | Focus |
|-------|--------------|-------|
| **MedSAM** | 1.5M medical images | General medical imaging |
| **SAM-Med2D** | 4.6M medical images | 2D medical segmentation |
| **SurgicalSAM** | Surgical video datasets | Instrument segmentation |

**Important Note**: These are image models, not video models. They provide better segmentation accuracy on medical content but lack temporal propagation. A hybrid approach would combine them with video tracking.

### 3.2 Surgical Video Challenges

| Challenge | Required Capability |
|-----------|-------------------|
| Instrument occlusion | Object re-identification after occlusion |
| Blood/fluid obscuring view | Robust tracking through visual noise |
| Fast instrument movement | High frame rate processing |
| Fine instrument tips | Sub-pixel accuracy |
| Multiple similar instruments | Distinct object ID tracking |
| Long procedures | Long-term memory without drift |

---

## 4. Benchmark Performance

### 4.1 Standard Datasets

| Model | DAVIS J&F | YouTube-VOS | MOSE (complex) |
|-------|-----------|-------------|----------------|
| SAM 2 Large | 89.3 | 85.0 | 74.5 |
| SAM 2 Base | 87.5 | 83.2 | 71.2 |
| Cutie | 88.8 | 84.2 | 73.8 |
| XMem | 87.7 | 85.5 | 69.4 |
| DEVA | 87.0 | 83.0 | 68.2 |

*MOSE dataset contains complex scenes with occlusions and deformations - most similar to surgical scenarios*

### 4.2 Inference Speed

| Model | FPS (typical) | GPU Memory |
|-------|--------------|------------|
| SAM 2 Large | ~30 | High |
| SAM 2 Base | ~44 | Medium |
| Cutie | ~50 | Medium |
| XMem | ~30 | Medium |
| DEVA | ~25 | Medium-High |

---

## 5. Recommended Approach

### 5.1 Primary Recommendation: SAM 2

**Rationale**:
- Official Meta support with active development
- Best documentation and community adoption
- Unified image + video capability
- Proven performance across benchmarks
- Direct upgrade path from current SAM implementation

### 5.2 Secondary Recommendation: Cutie (Optional - Deprioritized)

**Original Rationale**:
- Superior long-video stability
- Better suited for multi-hour surgical procedures

**Updated Status**: With < 1 hour video constraint, Cutie's long-video advantages are less relevant. SAM 2 handles this duration well. Cutie evaluation moved to optional/future consideration.

### 5.3 Future Consideration: Hybrid Approach

For maximum accuracy on medical content:
```
Hybrid Pipeline:
1. Initial Segmentation → MedSAM or SurgicalSAM (medical-tuned accuracy)
2. Temporal Propagation → Cutie or XMem (long-video stability)
3. Interactive Refinement → SAM 2 (user corrections)
```

---

## 6. Implementation Phases

### Phase 1: SAM 2 Core Integration
**Goal**: Replace frame-by-frame SAM with video-aware SAM 2

**Scope**:
- Deploy SAM 2 model in backend service
- Implement video session management
- Add mask propagation capability
- Create new API endpoints for video annotation
- Update frontend to session-based workflow

**Expected Outcome**:
- User clicks once → mask propagates to all frames
- 10-50x reduction in annotation time

### Phase 2: Temporal Refinement Tools
**Goal**: Enable efficient correction of propagated masks

**Scope**:
- Add keyframe navigation (jump to frames where masks need correction)
- Implement confidence visualization
- Add bidirectional propagation controls
- Create "batch review" interface for quality assurance

**Expected Outcome**:
- Easy identification of frames needing correction
- Streamlined refinement workflow

### Phase 3: Multi-Object Tracking
**Goal**: Support annotation of multiple objects simultaneously

**Scope**:
- Object ID management (add, remove, rename tracked objects)
- Per-object category assignment
- Object-level timeline visualization
- Occlusion handling and re-identification

**Expected Outcome**:
- Annotate entire surgical scene (multiple instruments, anatomy) in one session

### Phase 4: Medical-Specific Optimizations (Optional)
**Goal**: Maximize accuracy for surgical content

**Scope**:
- Evaluate MedSAM/SurgicalSAM integration
- Consider hybrid architecture with DEVA
- Fine-tune on internal surgical dataset if available
- Implement class-specific tracking behavior

**Expected Outcome**:
- Improved segmentation accuracy on surgical instruments and anatomy

### Phase 5: Cutie Evaluation (Parallel Track)
**Goal**: Determine if Cutie provides benefits over SAM 2

**Scope**:
- Implement Cutie as alternative backend
- Run comparative evaluation on sample surgical videos
- Measure: accuracy, speed, long-video stability, user effort
- Decision point: adopt Cutie or stay with SAM 2

---

## 7. Architecture Changes Required

### 7.1 Backend Changes

| Component | Current | Proposed |
|-----------|---------|----------|
| Model Service | SAM (image-based) | SAM 2 (video-based) |
| Session Management | None | Video annotation sessions |
| API Pattern | Single-frame requests | Session-based with propagation |
| Memory Management | Stateless | Stateful video sessions |
| Caching | Frame-level | Video-level with object memory |

### 7.2 Frontend Changes

| Component | Current | Proposed |
|-----------|---------|----------|
| Workflow | Frame-by-frame | Session-based with propagation |
| Object Management | None | Multi-object tracking UI |
| Timeline | Frame navigation only | Keyframe markers, object timelines |
| Controls | Point/Box per frame | Add object, propagate, refine |
| Feedback | Current frame only | All-frame preview, confidence display |

### 7.3 Database Changes

| Addition | Purpose |
|----------|---------|
| Annotation Sessions | Track active video annotation sessions |
| Tracked Objects | Per-video object identity and metadata |
| Propagation History | Track which frames were auto-propagated vs manually refined |
| Object-Frame Mapping | Link objects to their masks across all frames |

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SAM 2 performance on surgical content | Medium | High | Early prototype testing on sample videos |
| Memory usage for long videos | **Low** | Low | < 1 hour constraint makes this manageable |
| User learning curve | Low | Low | Gradual UI transition, keep frame-by-frame as fallback |
| Integration complexity | Medium | Medium | Phased rollout, maintain backward compatibility |
| Model download size (~2GB) | Low | Low | Pre-download during deployment |
| **Cloud GPU latency** | Medium | Medium | Keep model warm, use regional deployment |
| **Cloud GPU availability** | Low | High | Use provider with good capacity, implement queue |
| **Cloud costs exceeding budget** | Medium | Medium | Implement usage monitoring, session timeouts |
| **Session state loss** | Low | Medium | Persist session state to Redis with TTL |
| **Concurrent session conflicts** | Low | Low | Proper session isolation per user |

---

## 9. Success Metrics

| Metric | Current Baseline | Target |
|--------|-----------------|--------|
| Clicks per 100 frames | 100+ | < 10 |
| Time to annotate 1-hour video | 8+ hours | < 2 hours |
| Temporal consistency (IoU between frames) | ~70% | > 95% |
| User satisfaction | N/A | Survey after pilot |
| Training model performance | Baseline | >5% improvement |

---

## 10. Project Constraints (Confirmed)

| Question | Answer | Impact on Plan |
|----------|--------|----------------|
| **Video Length** | < 1 hour | SAM 2 is sufficient; Cutie/XMem long-video optimizations less critical |
| **Concurrent Users** | ~10 | Need session management + GPU queue or multi-instance |
| **Migration** | Not required | Clean schema design, no legacy concerns |
| **GPU Resources** | Cloud-based (online) | Need cloud GPU infrastructure (AWS/GCP/Azure/RunPod) |

---

## 11. Cloud GPU Infrastructure

### 11.1 Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Cloud Architecture                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐ │
│  │   Frontend   │────▶│  Web Backend │────▶│  GPU Service (SAM2)  │ │
│  │   (Vercel/   │     │  (Container) │     │  (Cloud GPU)         │ │
│  │   Netlify)   │     │              │     │                      │ │
│  └──────────────┘     └──────────────┘     └──────────────────────┘ │
│                              │                       │               │
│                              ▼                       ▼               │
│                       ┌──────────────┐     ┌──────────────────────┐ │
│                       │  PostgreSQL  │     │  Redis (Sessions)    │ │
│                       │  + MinIO     │     │  + Job Queue         │ │
│                       └──────────────┘     └──────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 Cloud GPU Options

| Provider | GPU Option | Cost (approx) | Best For |
|----------|-----------|---------------|----------|
| **AWS** | g5.xlarge (A10G) | ~$1/hr | Production, reliability |
| **GCP** | a2-highgpu-1g (A100) | ~$3/hr | High performance |
| **Azure** | NC6s_v3 (V100) | ~$2/hr | Enterprise integration |
| **RunPod** | RTX 4090 | ~$0.50/hr | Cost-effective |
| **Lambda Labs** | A10 | ~$0.60/hr | ML-focused |
| **Modal** | Serverless GPU | Pay per second | Bursty workloads |
| **Replicate** | Serverless | Pay per prediction | Simplest integration |

### 11.3 Recommended: Serverless GPU Approach

For 10 concurrent users with variable workloads, **serverless GPU** is recommended:

**Option A: Modal.com**
- Pay only when GPU is in use
- Auto-scaling from 0 to N instances
- Built-in queue management
- ~$0.001 per second of GPU time

**Option B: Replicate**
- Pre-built SAM 2 deployment available
- Simple API integration
- No infrastructure management
- Higher per-prediction cost but zero ops burden

**Option C: Self-managed (AWS/GCP)**
- Deploy SAM 2 service on GPU instances
- Use Kubernetes with GPU node pools
- Implement job queue (Redis + Celery/Bull)
- More control, more operational overhead

### 11.4 Session Management for 10 Users

```
Session Architecture:
├── User starts annotation session
│   └── Backend creates session ID, stores in Redis
├── Video uploaded to cloud storage (S3/GCS/MinIO)
├── SAM 2 service initializes video (loads into GPU memory)
│   └── Session state stored with TTL (e.g., 30 min inactive timeout)
├── User interactions sent to their specific session
└── Session cleanup on timeout or explicit close
```

**Scaling Strategy**:
- 1 GPU can handle 2-3 concurrent sessions (with model sharing)
- For 10 users: 3-4 GPU instances or serverless scaling
- Queue system for burst handling (user waits if all GPUs busy)

### 11.5 Latency Considerations

| Operation | Target Latency | Strategy |
|-----------|---------------|----------|
| Single frame prediction | < 500ms | Keep model warm in GPU memory |
| Full video propagation | < 30s for 1-hour video | Batch processing, stream results |
| Interactive refinement | < 300ms | Prioritize active session |

**Latency Optimization**:
- Keep SAM 2 model loaded (no cold start)
- Use WebSocket for real-time updates during propagation
- Pre-extract video frames to cloud storage
- Stream mask results as they're generated

### 11.6 Cost Estimation (10 Users)

| Scenario | Monthly Estimate |
|----------|-----------------|
| **Light usage** (2 hrs/user/day) | ~$200-400/month |
| **Moderate usage** (4 hrs/user/day) | ~$400-800/month |
| **Heavy usage** (8 hrs/user/day) | ~$800-1500/month |

*Based on serverless GPU pricing; dedicated instances may be more cost-effective for heavy, predictable usage*

---

## 12. Updated Recommendations

### 12.1 Model Choice: SAM 2 (Confirmed)

Given < 1 hour video constraint:
- **SAM 2 is the clear choice** - handles this duration easily
- Cutie/XMem evaluation can be **deprioritized** (Phase 5 becomes optional)
- No need for specialized long-video memory management

### 12.2 Infrastructure Choice: Serverless GPU

For 10 users with cloud requirement:
- **Recommended: Modal or Replicate** for simplicity
- **Alternative: AWS/GCP with auto-scaling** for more control
- Implement session-based job queue regardless of platform

### 12.3 Simplified Phase Plan

| Phase | Priority | Notes |
|-------|----------|-------|
| Phase 1: SAM 2 Integration | High | Core functionality |
| Phase 2: Temporal Refinement | High | Essential for usability |
| Phase 3: Multi-Object Tracking | Medium | Important for surgical scenes |
| Phase 4: Medical Optimization | Low | Only if accuracy insufficient |
| Phase 5: Cutie Evaluation | **Removed** | Not needed for < 1 hour videos |

---

## 13. Implementation Status (December 2024)

### Completed ✅

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: SAM 2 Core Integration | ✅ Complete | Backend and frontend integrated |
| Phase 2: Temporal Refinement | 🟡 Partial | API exists, UI pending |
| Phase 3: Multi-Object Tracking | 🟡 Partial | Backend supports it, UI basic |
| Phase 4: Medical Optimization | ⬜ Not started | |

### Architecture Implemented

**Backend (sam-service)**:
- SAM 2 video predictor with session management
- REST API endpoints for all core operations
- Resource management (session limits, auto-cleanup)
- Video frame extraction to JPEG format

**Frontend (web-frontend)**:
- `SAM2Controls.tsx` - UI component for SAM 2 workflow
- `sam2Slice.ts` - Redux state management with async thunks
- TypeScript interfaces for all SAM 2 types
- API client for SAM 2 service

### Files Created/Modified

**New Files**:
- `web-frontend/src/components/annotation/SAM2Controls.tsx`
- `web-frontend/src/store/slices/sam2Slice.ts`

**Modified Files**:
- `web-frontend/src/pages/AnnotationPage.tsx` - SAM2Controls integration
- `web-frontend/src/store/store.ts` - sam2 reducer added
- `web-frontend/src/types/index.ts` - SAM2 types
- `web-frontend/src/utils/api.ts` - sam2API client

### Remaining Work

1. **Session Management (Milestone 4)**: Add Redis for distributed session state
2. **Refinement UI (Milestone 5)**: UI for correcting masks on specific frames
3. **Multi-Object UI (Milestone 6)**: Full object management panel
4. **Persistence (Milestone 7)**: Save propagated masks to database
5. **Cloud Deployment (Milestone 8)**: Deploy SAM 2 to cloud GPU

See `SAM2_IMPLEMENTATION_TODO.md` for detailed task tracking.

---

## 14. Next Steps

1. ~~**Review this document** with stakeholders~~ ✅
2. ~~**Set up SAM 2 prototype** on sample video~~ ✅
3. **Complete Milestone 4**: Add Redis session management
4. **Complete Milestone 5**: Refinement UI for mask corrections
5. **Select cloud GPU provider** (recommend Modal or Replicate for fastest start)
6. **Begin Phase 4** if accuracy needs improvement on medical content

---

## Appendix A: Model Resources

| Model | Repository | License |
|-------|------------|---------|
| SAM 2 | github.com/facebookresearch/segment-anything-2 | Apache 2.0 |
| Cutie | github.com/hkchengrex/Cutie | MIT |
| XMem | github.com/hkchengrex/XMem | MIT |
| DEVA | github.com/hkchengrex/Tracking-Anything-with-DEVA | MIT |
| MedSAM | github.com/bowang-lab/MedSAM | Apache 2.0 |

## Appendix B: Hardware Requirements

| Model | Minimum GPU | Recommended GPU | VRAM |
|-------|------------|-----------------|------|
| SAM 2 Tiny | GTX 1080 | RTX 3080 | 8GB |
| SAM 2 Base | RTX 2080 | RTX 3090 | 12GB |
| SAM 2 Large | RTX 3080 | RTX 4090 / A100 | 16GB+ |
| Cutie | GTX 1080 | RTX 3080 | 8GB |
| XMem | GTX 1080 | RTX 3080 | 8GB |

---

*Document Version: 1.2*
*Created: December 2024*
*Updated: December 2024*
*Status: Phase 1 Complete, Phase 2-3 In Progress*

### Changelog
- **v1.2**: Added implementation status section. Milestone 1-3 complete (Dec 2024). Frontend SAM2 integration implemented with Redux state management.
- **v1.1**: Added cloud GPU infrastructure section, updated based on confirmed constraints (< 1 hour videos, 10 concurrent users, cloud GPU requirement, no migration needed). Deprioritized Cutie evaluation. Added session management and cost estimates.
