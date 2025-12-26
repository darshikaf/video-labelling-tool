# System Optimization Summary

**Date:** 2025-12-13
**Issue:** Computer overheating due to runaway SAM 2 process
**Status:** ✅ RESOLVED

---

## Problem Identified

A SAM 2 test script was running wild with:
- **503.7% CPU usage** (5+ cores maxed out)
- **3.4GB RAM consumption**
- **26+ minutes of continuous processing**
- Processing video frames without any resource limits

**Root Cause:** No resource management, session limits, or cleanup mechanisms in place.

---

## Fixes Implemented

### 1. Killed Runaway Process ✅

```bash
# Terminated PIDs: 1554, 1553, 1547
kill -9 1554 1553 1547
```

CPU usage is now back to normal (< 1%).

### 2. Added Resource Limits to SAM2VideoPredictor ✅

**File:** `sam-service/core/sam2_video_predictor.py`

**Changes:**
- Max concurrent sessions: **2** (configurable via env)
- Session timeout: **5 minutes** (down from 30 minutes)
- Max video frames: **300** (~10 seconds at 30fps)
- Max frame dimension: **1920 pixels** (Full HD)
- Automatic session cleanup when limit reached

**Impact:** Prevents loading huge videos that exhaust system memory.

### 3. Implemented Auto-Cleanup Background Task ✅

**File:** `sam-service/main.py`

**Changes:**
- Background task runs every **60 seconds**
- Automatically removes expired/idle sessions
- Prevents memory leaks from forgotten sessions
- Graceful shutdown cleanup

**Impact:** Sessions are cleaned up automatically, freeing resources.

### 4. Made Legacy SAM Model Lazy-Loading ✅

**File:** `web-backend/app/core/sam_model.py`

**Changes:**
- Model only loads on first use (not at startup)
- Saves ~2GB RAM and GPU memory when not in use
- Keeps functionality for single-frame predictions

**Impact:** Removes duplicate 375MB SAM model from always being loaded.

### 5. Added Docker Resource Limits ✅

**File:** `docker-compose.yml`

**Changes:**
```yaml
Service         CPU Limit    Memory Limit    Notes
-----------     ---------    ------------    -----
frontend        2 cores      2GB             Node.js + Vite
backend         4 cores      4GB             FastAPI + single-frame SAM
sam-service     6 cores      8GB             SAM 2 video processing (most intensive)
database        2 cores      2GB             PostgreSQL
redis           1 core       512MB           Redis cache
minio           2 cores      2GB             Object storage
```

**Total System Resources:**
- **Max CPU:** 17 cores (if all services at peak)
- **Max RAM:** 18.5GB (if all services at peak)

**Impact:** Docker prevents any single service from monopolizing system resources.

### 6. Configured Development-Friendly Defaults ✅

**Files:**
- `sam-service/.env.example`
- `sam-service/.env.development`
- `docker-compose.yml`

**Development Settings:**
```bash
SAM2_MODEL_SIZE=tiny              # Smallest model (38MB vs 375MB)
SAM2_DEVICE=cpu                   # Use CPU (safer than GPU for dev)
SESSION_TIMEOUT=300               # 5 minutes
MAX_CONCURRENT_SESSIONS=2         # Max 2 sessions
MAX_VIDEO_FRAMES=300              # ~10 second clips
MAX_FRAME_DIMENSION=1920          # Full HD max
```

**Impact:** Safe defaults prevent overheating during development.

### 7. Added Progress Monitoring ✅

**File:** `sam-service/core/sam2_video_predictor.py`

**Changes:**
- Logs propagation progress every 50 frames
- Shows FPS and timing information
- Helps identify performance bottlenecks

**Impact:** Visibility into what's happening during intensive operations.

---

## Configuration Guide

### Quick Start (Development)

Use the provided `.env.development` file:

```bash
cd sam-service
cp .env.development .env
```

### For Different System Specs

#### 8GB RAM System
```bash
SAM2_MODEL_SIZE=tiny
MAX_CONCURRENT_SESSIONS=1
MAX_VIDEO_FRAMES=150
```

#### 16GB RAM System (Current Recommendation)
```bash
SAM2_MODEL_SIZE=small
MAX_CONCURRENT_SESSIONS=2
MAX_VIDEO_FRAMES=300
```

#### 32GB RAM + GPU System
```bash
SAM2_MODEL_SIZE=base_plus
SAM2_DEVICE=auto
MAX_CONCURRENT_SESSIONS=3
MAX_VIDEO_FRAMES=600
```

---

## Files Modified

1. ✅ `sam-service/core/sam2_video_predictor.py` - Resource limits and safety checks
2. ✅ `sam-service/main.py` - Auto-cleanup background task
3. ✅ `web-backend/app/core/sam_model.py` - Lazy-loading for duplicate SAM model
4. ✅ `docker-compose.yml` - Docker resource limits for all services
5. ✅ `sam-service/RESOURCE_MANAGEMENT.md` - Comprehensive documentation (new)
6. ✅ `sam-service/.env.example` - Configuration template (new)
7. ✅ `sam-service/.env.development` - Development defaults (new)

---

## Resource Estimates

### Per Video Session (with default limits)

| Component           | Memory Usage | Notes                          |
|---------------------|--------------|--------------------------------|
| Video frames (300)  | ~1.8GB       | Uncompressed RGB frames        |
| SAM 2 model (tiny)  | ~1GB         | Shared across sessions         |
| Inference state     | ~500MB       | Per session                    |
| **Total per session** | **~2.3GB**  | With tiny model                |

### Model Size Comparison

| Model     | Size  | Speed     | Accuracy | GPU Memory | Use Case              |
|-----------|-------|-----------|----------|------------|-----------------------|
| tiny      | 38MB  | Very Fast | Good     | ~1GB       | Development, Testing  |
| small     | 181MB | Fast      | Better   | ~2GB       | Light Production      |
| base_plus | 375MB | Medium    | Great    | ~4GB       | Production            |
| large     | 814MB | Slow      | Best     | ~8GB       | High Accuracy         |

---

## Testing the Fixes

### 1. Verify No Runaway Processes

```bash
ps aux | grep python | grep sam
```

Should show minimal CPU usage (< 5%).

### 2. Test Docker with Resource Limits

```bash
docker-compose up --build
```

Monitor resource usage:
```bash
docker stats
```

### 3. Test Session Limits

Try creating 3 sessions simultaneously - the 3rd should fail with a clear error message.

### 4. Test Auto-Cleanup

Create a session, wait 5 minutes, check logs:
```bash
docker logs sam-service -f
```

Should see: `Auto-cleanup: Removed 1 expired sessions`

---

## Performance Tips

### For Development
1. ✅ Use `SAM2_MODEL_SIZE=tiny`
2. ✅ Use `SAM2_DEVICE=cpu`
3. ✅ Keep videos under 10 seconds
4. ✅ Close Docker containers when not in use

### For Production
1. Use `SAM2_MODEL_SIZE=base_plus` or `large`
2. Use `SAM2_DEVICE=auto` (GPU if available)
3. Increase `MAX_VIDEO_FRAMES` based on available RAM
4. Monitor logs for resource warnings

### Video Preprocessing
```bash
# Reduce resolution to 720p
ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4

# Extract 10-second clip
ffmpeg -i input.mp4 -t 10 -c copy output.mp4

# Reduce frame rate to 15fps
ffmpeg -i input.mp4 -r 15 output.mp4
```

---

## Monitoring Commands

### Check System Resources
```bash
# macOS
top -o cpu

# Linux
htop

# Docker containers
docker stats
```

### Check SAM Service Logs
```bash
docker logs sam-service -f
```

### Check for Memory Leaks
```bash
# List all sessions
curl http://localhost:8002/health

# Force cleanup
curl -X POST http://localhost:8002/cleanup
```

---

## Rollback Instructions

If you need to revert changes:

```bash
git checkout HEAD~1 sam-service/core/sam2_video_predictor.py
git checkout HEAD~1 sam-service/main.py
git checkout HEAD~1 docker-compose.yml
```

---

## Next Steps

### Recommended Improvements

1. **Add metrics endpoint** - Track CPU/memory usage per session
2. **Implement video streaming** - Load frames on-demand instead of all at once
3. **Add request queuing** - Queue requests when at session limit
4. **Implement frame caching** - Cache processed frames to disk
5. **Add GPU memory monitoring** - Track VRAM usage when using CUDA

### Optional Enhancements

1. Use Redis for distributed session management
2. Add rate limiting per user
3. Implement progressive video loading
4. Add WebSocket for real-time progress updates
5. Create admin dashboard for monitoring

---

## Support

For issues or questions:
1. Check logs: `docker logs sam-service -f`
2. Review `sam-service/RESOURCE_MANAGEMENT.md`
3. Check system resources: `docker stats`
4. File an issue on GitHub

---

## Summary Checklist

- [x] Killed runaway process
- [x] Added resource limits to video loading
- [x] Implemented auto-cleanup (runs every 60s)
- [x] Added session limits (max 2 concurrent)
- [x] Made legacy SAM model lazy-loading
- [x] Added Docker resource limits
- [x] Created development configuration
- [x] Added progress monitoring
- [x] Created comprehensive documentation

**System Status:** ✅ Stable and protected against resource exhaustion
