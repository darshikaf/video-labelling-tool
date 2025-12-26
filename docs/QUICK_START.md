# Quick Start Guide - Post Optimization

## What Changed?

Your video labeling tool has been optimized to prevent system overheating. Here's what you need to know:

### ✅ Immediate Fixes Applied
- Killed runaway SAM 2 process (was using 500%+ CPU)
- Added resource limits across all services
- Configured safe defaults for development

### 🎯 Key Changes
1. **Session limits**: Max 2 concurrent video sessions
2. **Video limits**: Max 300 frames (~10 seconds) per video
3. **Auto-cleanup**: Idle sessions removed after 5 minutes
4. **Smaller model**: Using "tiny" model for development (38MB vs 375MB)
5. **Docker limits**: Each service has CPU/RAM caps

---

## Getting Started

### Option 1: Using Docker (Recommended)

```bash
# Start all services with resource limits
docker-compose up --build

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - SAM Service: http://localhost:8002
```

### Option 2: Running SAM Service Locally

```bash
cd sam-service

# Copy development configuration
cp .env.development .env

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the service
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

---

## Usage Guidelines

### ✅ DO:
- Use video clips under 10 seconds
- Close sessions when done
- Monitor logs for warnings
- Use 720p or 1080p videos (not 4K)
- Keep to 1-2 concurrent sessions

### ❌ DON'T:
- Upload full-length videos (split them into clips)
- Leave sessions idle for long periods
- Run multiple test scripts simultaneously
- Use 4K or higher resolution videos
- Exceed 2 concurrent sessions

---

## Video Preparation

Before uploading videos, process them to stay within limits:

```bash
# Extract 10-second clip
ffmpeg -i video.mp4 -t 10 -c copy clip.mp4

# Reduce to 720p
ffmpeg -i video.mp4 -vf scale=1280:720 output.mp4

# Combine both (10s clip at 720p)
ffmpeg -i video.mp4 -t 10 -vf scale=1280:720 output.mp4
```

---

## Configuration

### Development (Current Setup)
```bash
SAM2_MODEL_SIZE=tiny           # Fastest, smallest
SAM2_DEVICE=cpu                # Safer than GPU
MAX_CONCURRENT_SESSIONS=2      # Max 2 sessions
MAX_VIDEO_FRAMES=300           # ~10 seconds
```

### If You Have More RAM/Better Hardware

Edit `sam-service/.env`:

```bash
# For 32GB+ RAM with GPU:
SAM2_MODEL_SIZE=base_plus
SAM2_DEVICE=auto
MAX_CONCURRENT_SESSIONS=3
MAX_VIDEO_FRAMES=600
```

---

## Monitoring

### Check Service Health

```bash
# SAM service health
curl http://localhost:8002/health

# Response shows:
# - active_sessions: current sessions
# - model_loaded: true/false
# - status: healthy/simulation
```

### Monitor Resources

```bash
# Watch Docker container resources
docker stats

# Check SAM service logs
docker logs sam-service -f
```

### Force Cleanup (if needed)

```bash
curl -X POST http://localhost:8002/cleanup
```

---

## Troubleshooting

### Issue: Service won't start
**Solution:** Check if ports are already in use
```bash
lsof -i :8002
kill -9 <PID>
```

### Issue: "Maximum concurrent sessions reached"
**Solution:** Wait 5 minutes for auto-cleanup or manually cleanup:
```bash
curl -X POST http://localhost:8002/cleanup
```

### Issue: Video too large
**Solution:** Reduce video size:
```bash
# Get video info
ffprobe video.mp4

# If over 10 seconds or 1080p, reduce:
ffmpeg -i video.mp4 -t 10 -vf scale=1280:720 output.mp4
```

### Issue: System still hot
**Solutions:**
1. Reduce to 1 concurrent session
2. Use an even smaller model: `SAM2_MODEL_SIZE=tiny`
3. Reduce frame limit: `MAX_VIDEO_FRAMES=150`
4. Stop Docker when not in use: `docker-compose down`

---

## Important Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Docker configuration with resource limits |
| `sam-service/.env` | SAM service configuration |
| `sam-service/RESOURCE_MANAGEMENT.md` | Detailed resource documentation |
| `OPTIMIZATION_SUMMARY.md` | Complete list of changes made |

---

## Resource Limits Summary

| Service | CPU Limit | RAM Limit | Purpose |
|---------|-----------|-----------|---------|
| frontend | 2 cores | 2GB | React UI |
| backend | 4 cores | 4GB | API server |
| sam-service | 6 cores | 8GB | Video ML processing |
| database | 2 cores | 2GB | PostgreSQL |
| redis | 1 core | 512MB | Cache |
| minio | 2 cores | 2GB | File storage |
| **Total** | **17 cores** | **18.5GB** | Full stack |

---

## Performance Tips

1. **Close Docker when not coding:**
   ```bash
   docker-compose down
   ```

2. **Use smaller videos for testing:**
   - Keep under 10 seconds
   - Use 720p resolution
   - Test with 1-2 objects maximum

3. **Monitor your system:**
   - Watch Activity Monitor (Mac) or Task Manager (Windows)
   - Check Docker stats: `docker stats`

4. **Restart if needed:**
   ```bash
   docker-compose restart sam-service
   ```

---

## Development Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Watch logs (optional)
docker logs sam-service -f

# 3. Use the application at http://localhost:3000

# 4. When done, stop services
docker-compose down
```

---

## Using SAM 2 Video Annotation

### Step-by-Step Guide

1. **Start services**:
   ```bash
   docker-compose up -d
   ```

2. **Open the application** at http://localhost:3000

3. **Navigate to a video** in a project

4. **Enable SAM 2 Mode**:
   - Look for the "SAM 2 Video Mode" panel
   - Toggle the switch to ON (panel will highlight blue)

5. **Initialize Session**:
   - Click "Initialize Session" button
   - Wait for "Session Active" status (shows video info: frames, fps, dimensions)

6. **Add Objects to Track**:
   - Click on an object in the video frame
   - Left-click = positive point (include this area)
   - Right-click = negative point (exclude this area)
   - The mask appears immediately for that frame

7. **Propagate to All Frames**:
   - Click "Propagate to All Frames" button
   - Watch the progress bar
   - Masks will be generated for every frame

8. **Review Results**:
   - Scrub the timeline to see masks on different frames
   - Object list shows how many frames have masks

9. **Close Session** when done:
   - Click "Close Session" or toggle SAM 2 Mode off

### SAM 2 Frontend Components

| File | Purpose |
|------|---------|
| `SAM2Controls.tsx` | UI panel with toggle, session controls, object list |
| `sam2Slice.ts` | Redux state for sessions, objects, masks |
| `api.ts` (sam2API) | API client for SAM 2 service endpoints |

### Troubleshooting SAM 2 UI

**"Failed to initialize session"**:
- Check if SAM 2 service is running: `docker logs sam-service`
- Ensure video exists and is accessible
- Video may exceed frame/dimension limits

**"Maximum concurrent sessions reached"**:
- Wait 5 minutes for session timeout, or
- Click "Close Session" on any active sessions

**Masks not appearing**:
- Check browser console for errors
- Verify the canvas is properly rendering
- Try refreshing the page

---

## Next Steps

1. ✅ Test with a short video clip (< 10 seconds)
2. ✅ Monitor resource usage with `docker stats`
3. ✅ Check logs for any warnings
4. ✅ Verify sessions auto-cleanup after 5 minutes

---

## Need Help?

1. Check logs: `docker logs sam-service -f`
2. Review `RESOURCE_MANAGEMENT.md` for detailed info
3. Check `OPTIMIZATION_SUMMARY.md` for what changed
4. Check `SAM2_IMPLEMENTATION_TODO.md` for implementation progress
5. File an issue if problems persist

---

**Status:** ✅ System is now optimized and protected against overheating!
