# SAM Service Resource Management

## Overview

The SAM 2 service has been updated with comprehensive resource management to prevent system overheating and memory exhaustion.

## Key Changes

### 1. Session Limits
- **Max Concurrent Sessions**: Limited to 2 by default (configurable)
- **Session Timeout**: Reduced from 30 minutes to 5 minutes
- **Auto-cleanup**: Background task runs every 60 seconds to remove expired sessions

### 2. Video Limits
- **Max Video Frames**: 300 frames (~10 seconds at 30fps)
- **Max Frame Dimension**: 1920 pixels (width or height)
- These limits prevent loading huge videos that exhaust memory

### 3. Auto-Cleanup
- Background task automatically removes idle sessions
- Runs every 60 seconds
- Sessions expire after 5 minutes of inactivity (configurable)

### 4. Monitoring
- Progress logging during mask propagation
- Resource warnings when approaching session limits
- Detailed timing information for operations

## Environment Variables

You can configure these limits via environment variables:

```bash
# Session management
SESSION_TIMEOUT=300              # Session timeout in seconds (default: 300 = 5 minutes)
MAX_CONCURRENT_SESSIONS=2        # Maximum concurrent sessions (default: 2)

# Video limits
MAX_VIDEO_FRAMES=300            # Maximum frames to load (default: 300)
MAX_FRAME_DIMENSION=1920        # Maximum width/height (default: 1920)

# Model settings
SAM2_MODEL_SIZE=base_plus       # Model size: tiny, small, base_plus, large
SAM2_DEVICE=auto                # Device: auto, cpu, cuda
MODEL_DIR=/app/models           # Model checkpoint directory
```

## Usage Examples

### Docker Compose

```yaml
sam-service:
  environment:
    - SESSION_TIMEOUT=300
    - MAX_CONCURRENT_SESSIONS=2
    - MAX_VIDEO_FRAMES=300
    - MAX_FRAME_DIMENSION=1920
```

### Direct Python

```python
predictor = SAM2VideoPredictor(
    session_timeout=300,           # 5 minutes
    max_concurrent_sessions=2,
    max_video_frames=300,
    max_frame_dimension=1920
)
```

## Best Practices

### 1. Video Preparation
- **Keep videos short**: Use 10-second clips for annotation
- **Reduce resolution**: 1080p or lower recommended
- **Split long videos**: Process in chunks if needed

### 2. Session Management
- **Close sessions**: Always close sessions when done
- **Use short clips**: Test with small videos first
- **Monitor logs**: Watch for resource warnings

### 3. Performance Optimization
- **Use smaller models**: Start with `tiny` or `small` for testing
- **Limit concurrent users**: Keep to 2-3 simultaneous sessions
- **CPU mode for testing**: Use `SAM2_DEVICE=cpu` for development

## Common Issues

### Issue: "Maximum concurrent sessions reached"
**Solution**: Wait for sessions to expire (5 minutes) or manually close unused sessions via `/session/close` endpoint.

### Issue: "Video has too many frames"
**Solution**:
- Use a shorter video clip (≤10 seconds)
- Increase `MAX_VIDEO_FRAMES` if you have sufficient RAM
- Rule of thumb: Each frame uses ~6MB RAM (for 1080p video)

### Issue: "Video dimensions exceed maximum"
**Solution**:
- Reduce video resolution before upload
- Increase `MAX_FRAME_DIMENSION` if needed
- Transcode video to lower resolution: `ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4`

### Issue: System still overheating
**Solutions**:
1. Reduce `MAX_CONCURRENT_SESSIONS` to 1
2. Use a smaller model: `SAM2_MODEL_SIZE=tiny`
3. Reduce `MAX_VIDEO_FRAMES` to 150 (5 seconds)
4. Use CPU mode: `SAM2_DEVICE=cpu`
5. Close other resource-intensive applications

## Monitoring Endpoints

### Check Service Health
```bash
curl http://localhost:8002/health
```

Response includes:
- `active_sessions`: Current number of active sessions
- `model_loaded`: Whether SAM 2 model is loaded
- `status`: Service status

### Check Session Status
```bash
curl http://localhost:8002/session/{session_id}
```

Response includes:
- `idle_time`: Seconds since last activity
- `total_frames`: Number of frames in video
- `objects`: Tracked objects

### Manual Cleanup
```bash
curl -X POST http://localhost:8002/cleanup
```

Forces immediate cleanup of expired sessions.

## Resource Estimates

### Memory Usage (per session)
- **Video frames**: ~6MB per frame (1080p RGB)
  - 300 frames = ~1.8GB
- **SAM 2 model**: ~2-4GB (depending on size)
- **Inference state**: ~500MB-1GB per session
- **Total**: ~4-7GB per active session

### CPU Usage
- **Model loading**: High CPU/GPU usage for 5-10 seconds
- **Mask propagation**: High CPU/GPU usage (5-30 seconds per video)
- **Idle sessions**: Minimal CPU usage

### Recommended Hardware
- **Minimum**: 8GB RAM, 4-core CPU
- **Recommended**: 16GB RAM, 8-core CPU, GPU (optional)
- **Production**: 32GB RAM, 16-core CPU, NVIDIA GPU with 8GB+ VRAM

## Troubleshooting

### Check for Runaway Processes
```bash
# macOS/Linux
ps aux | grep python | grep sam

# Kill if needed
kill -9 <PID>
```

### Check System Resources
```bash
# macOS
top -o cpu

# Linux
htop

# Check GPU usage (if CUDA available)
nvidia-smi
```

### View Service Logs
```bash
# Docker
docker logs sam-service -f

# Direct run
tail -f /var/log/sam-service.log
```

## Contact

For issues or questions about resource management, please file an issue in the repository.
