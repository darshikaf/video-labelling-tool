"""
SAM 2 Video Annotation Service

This FastAPI service provides video-based segmentation using Meta's SAM 2 model.
It supports:
- Video session initialization
- Object tracking with point/box prompts
- Temporal mask propagation
- Mask refinement
- Multi-object tracking
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.sam2_video_predictor import SAM2VideoPredictor
from schemas import (
    AddObjectRequest,
    AddObjectResponse,
    AddObjectWithBoxRequest,
    CloseSessionRequest,
    CloseSessionResponse,
    FrameMask,
    GetFrameMasksRequest,
    GetFrameMasksResponse,
    HealthResponse,
    InitializeSessionRequest,
    InitializeSessionResponse,
    PropagateRequest,
    PropagateResponse,
    RefineRequest,
    RefineResponse,
    SessionStatusResponse,
    encode_mask,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global predictor instance
sam2_predictor: Optional[SAM2VideoPredictor] = None
cleanup_task: Optional[asyncio.Task] = None


async def auto_cleanup_sessions():
    """Background task that automatically cleans up expired sessions"""
    logger.info("Starting auto-cleanup background task (runs every 60 seconds)")
    while True:
        try:
            await asyncio.sleep(60)  # Run every 60 seconds
            if sam2_predictor:
                count = sam2_predictor.cleanup_expired_sessions()
                if count > 0:
                    logger.info(f"Auto-cleanup: Removed {count} expired sessions")
        except asyncio.CancelledError:
            logger.info("Auto-cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in auto-cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global sam2_predictor, cleanup_task

    logger.info("Starting SAM 2 Video Annotation Service...")

    # Determine model directory (use env var or default)
    model_dir = os.getenv("MODEL_DIR", str(Path(__file__).parent / "models"))

    # Initialize SAM 2 predictor with safer defaults
    sam2_predictor = SAM2VideoPredictor(
        model_size=os.getenv("SAM2_MODEL_SIZE", "base_plus"),
        model_dir=model_dir,
        device=os.getenv("SAM2_DEVICE", "auto"),
        session_timeout=int(
            os.getenv("SESSION_TIMEOUT", "300")
        ),  # 5 minutes (reduced from 30)
        max_concurrent_sessions=int(os.getenv("MAX_CONCURRENT_SESSIONS", "2")),
        max_video_frames=int(
            os.getenv("MAX_VIDEO_FRAMES", "300")
        ),  # ~10 seconds at 30fps
        max_frame_dimension=int(os.getenv("MAX_FRAME_DIMENSION", "1920")),
    )

    try:
        await sam2_predictor.initialize()
        logger.info("SAM 2 model loaded successfully")
    except Exception as e:
        logger.warning(f"SAM 2 model loading failed: {e}")
        logger.info("Running in simulation mode")

    # Start auto-cleanup background task
    cleanup_task = asyncio.create_task(auto_cleanup_sessions())

    yield

    # Cleanup on shutdown
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    if sam2_predictor:
        for session_id in list(sam2_predictor.sessions.keys()):
            sam2_predictor.close_session(session_id)
        logger.info("All sessions closed")


app = FastAPI(
    title="SAM 2 Video Annotation Service",
    description="Video-based segmentation with temporal propagation using Meta's SAM 2",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health & Status Endpoints
# ============================================================


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with service status"""
    active_sessions = len(sam2_predictor.sessions) if sam2_predictor else 0
    max_sessions = sam2_predictor.max_concurrent_sessions if sam2_predictor else 0

    # Log warning if approaching session limit
    if active_sessions >= max_sessions * 0.8:
        logger.warning(
            f"Approaching session limit: {active_sessions}/{max_sessions} sessions active"
        )

    return HealthResponse(
        message="SAM 2 Video Annotation Service",
        status="healthy"
        if sam2_predictor and sam2_predictor.is_loaded()
        else "simulation",
        model_loaded=sam2_predictor.is_loaded() if sam2_predictor else False,
        timestamp=time.time(),
        active_sessions=active_sessions,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        message="SAM 2 Video Annotation Service",
        status="healthy"
        if sam2_predictor and sam2_predictor.is_loaded()
        else "simulation",
        model_loaded=sam2_predictor.is_loaded() if sam2_predictor else False,
        timestamp=time.time(),
        active_sessions=len(sam2_predictor.sessions) if sam2_predictor else 0,
    )


# ============================================================
# Session Management Endpoints
# ============================================================


@app.post("/initialize", response_model=InitializeSessionResponse)
async def initialize_session(request: InitializeSessionRequest):
    """
    Initialize a new video annotation session.

    This loads the video into memory and prepares it for annotation.
    """
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    try:
        session = sam2_predictor.create_session(video_path=request.video_path)

        return InitializeSessionResponse(
            session_id=session.session_id,
            video_path=session.video_path,
            total_frames=session.total_frames,
            frame_width=session.frame_width,
            frame_height=session.frame_height,
            fps=session.fps,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404, detail=f"Video not found: {request.video_path}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize session: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize session: {str(e)}"
        )


@app.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get the status of an existing session"""
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    session = sam2_predictor.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    objects = []
    for obj_id, obj in session.objects.items():
        objects.append(
            {
                "object_id": obj.object_id,
                "name": obj.name,
                "category": obj.category,
                "color": list(obj.color),
                "frames_with_masks": len(obj.masks),
            }
        )

    return SessionStatusResponse(
        session_id=session.session_id,
        video_path=session.video_path,
        total_frames=session.total_frames,
        objects=objects,
        created_at=session.created_at,
        last_accessed=session.last_accessed,
        idle_time=session.idle_time,
    )


@app.post("/session/close", response_model=CloseSessionResponse)
async def close_session(request: CloseSessionRequest):
    """Close and cleanup a session"""
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    session = sam2_predictor.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=f"Session not found: {request.session_id}"
        )

    sam2_predictor.close_session(request.session_id)

    return CloseSessionResponse(
        message="Session closed successfully",
        session_id=request.session_id,
    )


# ============================================================
# Object Tracking Endpoints
# ============================================================


@app.post("/add-object", response_model=AddObjectResponse)
async def add_object(request: AddObjectRequest):
    """
    Add a new object to track using point prompts.

    Provide one or more points on a specific frame to define the object.
    Use positive labels (1) for points inside the object,
    and negative labels (0) for points outside.
    """
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    try:
        # Convert points to tuples
        points = [(p[0], p[1]) for p in request.points]

        result = sam2_predictor.add_object(
            session_id=request.session_id,
            frame_idx=request.frame_idx,
            object_id=request.object_id,
            points=points,
            labels=request.labels,
            name=request.name or "",
            category=request.category or "",
        )

        return AddObjectResponse(
            object_id=result["object_id"],
            name=result["name"],
            category=result["category"],
            color=list(result["color"]),
            frame_idx=result["frame_idx"],
            mask=encode_mask(result["mask"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add object: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add object: {str(e)}")


@app.post("/add-object-box", response_model=AddObjectResponse)
async def add_object_with_box(request: AddObjectWithBoxRequest):
    """
    Add a new object to track using a bounding box.

    Provide a bounding box [x1, y1, x2, y2] around the object.
    """
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    try:
        result = sam2_predictor.add_object_with_box(
            session_id=request.session_id,
            frame_idx=request.frame_idx,
            object_id=request.object_id,
            box=tuple(request.box),
            name=request.name or "",
            category=request.category or "",
        )

        return AddObjectResponse(
            object_id=result["object_id"],
            name=result["name"],
            category=result["category"],
            color=list(result["color"]),
            frame_idx=result["frame_idx"],
            mask=encode_mask(result["mask"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add object with box: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add object: {str(e)}")


# ============================================================
# Propagation Endpoints
# ============================================================


@app.post("/propagate", response_model=PropagateResponse)
async def propagate_masks(request: PropagateRequest):
    """
    Propagate masks from annotated frames to all other frames.

    This is the core SAM 2 feature that tracks objects across the video.
    """
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    try:
        result = sam2_predictor.propagate_masks(
            session_id=request.session_id,
            start_frame=request.start_frame,
            end_frame=request.end_frame,
            direction=request.direction or "both",
        )

        # Convert to response format
        frames = []
        for frame_idx, frame_masks in result["frames"].items():
            masks_encoded = {
                obj_id: encode_mask(mask) for obj_id, mask in frame_masks.items()
            }
            frames.append(FrameMask(frame_idx=frame_idx, masks=masks_encoded))

        # Sort by frame index
        frames.sort(key=lambda f: f.frame_idx)

        return PropagateResponse(
            session_id=result["session_id"],
            total_frames=result["total_frames"],
            frames=frames,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to propagate masks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to propagate: {str(e)}")


# ============================================================
# Refinement Endpoints
# ============================================================


@app.post("/refine", response_model=RefineResponse)
async def refine_mask(request: RefineRequest):
    """
    Add refinement points to correct a mask on a specific frame.

    Use this when the propagated mask has drifted or is inaccurate.
    """
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    try:
        # Convert points to tuples
        points = [(p[0], p[1]) for p in request.points]

        result = sam2_predictor.refine_mask(
            session_id=request.session_id,
            frame_idx=request.frame_idx,
            object_id=request.object_id,
            points=points,
            labels=request.labels,
        )

        return RefineResponse(
            object_id=result["object_id"],
            frame_idx=result["frame_idx"],
            mask=encode_mask(result["mask"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refine mask: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refine: {str(e)}")


# ============================================================
# Frame Mask Retrieval
# ============================================================


@app.post("/frame-masks", response_model=GetFrameMasksResponse)
async def get_frame_masks(request: GetFrameMasksRequest):
    """Get all object masks for a specific frame"""
    if not sam2_predictor:
        raise HTTPException(status_code=503, detail="SAM 2 service not initialized")

    try:
        masks = sam2_predictor.get_frame_masks(
            session_id=request.session_id,
            frame_idx=request.frame_idx,
        )

        masks_encoded = {obj_id: encode_mask(mask) for obj_id, mask in masks.items()}

        return GetFrameMasksResponse(
            frame_idx=request.frame_idx,
            masks=masks_encoded,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get frame masks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get masks: {str(e)}")


# ============================================================
# Background Tasks
# ============================================================


def cleanup_expired_sessions():
    """Background task to cleanup expired sessions"""
    if sam2_predictor:
        count = sam2_predictor.cleanup_expired_sessions()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")


@app.post("/cleanup")
async def trigger_cleanup(background_tasks: BackgroundTasks):
    """Manually trigger session cleanup"""
    background_tasks.add_task(cleanup_expired_sessions)
    return {"message": "Cleanup task scheduled"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
