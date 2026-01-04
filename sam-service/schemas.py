"""
SAM 2 Video Annotation Service Schemas

Request/response schemas for the SAM 2 video annotation API.
"""

import base64
import io
from typing import Dict, List, Optional

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

# ============================================================
# Session Management
# ============================================================


class InitializeSessionRequest(BaseModel):
    """Request to initialize a video annotation session"""

    video_path: str = Field(..., description="Path to the video file")
    model_size: Optional[str] = Field(
        default="base_plus",
        description="SAM 2 model size: tiny, small, base_plus, or large",
    )


class InitializeSessionResponse(BaseModel):
    """Response after initializing a video annotation session"""

    session_id: str = Field(..., description="Unique session identifier")
    video_path: str = Field(..., description="Path to the video file")
    total_frames: int = Field(..., description="Total number of frames in the video")
    frame_width: int = Field(..., description="Video frame width in pixels")
    frame_height: int = Field(..., description="Video frame height in pixels")
    fps: float = Field(..., description="Video frames per second")


class SessionStatusResponse(BaseModel):
    """Response with session status information"""

    session_id: str = Field(..., description="Session identifier")
    video_path: str = Field(..., description="Path to the video file")
    total_frames: int = Field(..., description="Total frames in video")
    objects: List[Dict] = Field(..., description="List of tracked objects")
    created_at: float = Field(..., description="Session creation timestamp")
    last_accessed: float = Field(..., description="Last access timestamp")
    idle_time: float = Field(..., description="Seconds since last access")


class CloseSessionRequest(BaseModel):
    """Request to close a session"""

    session_id: str = Field(..., description="Session identifier")


class CloseSessionResponse(BaseModel):
    """Response after closing a session"""

    message: str = Field(..., description="Status message")
    session_id: str = Field(..., description="Closed session ID")


# ============================================================
# Object Tracking
# ============================================================


class AddObjectRequest(BaseModel):
    """Request to add a new tracked object with point prompts"""

    session_id: str = Field(..., description="Session identifier")
    frame_idx: int = Field(..., description="Frame index to add object on")
    object_id: int = Field(..., description="Unique ID for this object")
    points: List[List[float]] = Field(
        ..., description="List of [x, y] point coordinates"
    )
    labels: List[int] = Field(
        ..., description="Point labels (1=positive/include, 0=negative/exclude)"
    )
    name: Optional[str] = Field(default="", description="Object name (e.g., 'Forceps')")
    category: Optional[str] = Field(
        default="", description="Object category (e.g., 'Instrument')"
    )


class AddObjectWithBoxRequest(BaseModel):
    """Request to add a new tracked object with bounding box"""

    session_id: str = Field(..., description="Session identifier")
    frame_idx: int = Field(..., description="Frame index to add object on")
    object_id: int = Field(..., description="Unique ID for this object")
    box: List[float] = Field(
        ..., description="Bounding box as [x1, y1, x2, y2]", min_length=4, max_length=4
    )
    name: Optional[str] = Field(default="", description="Object name")
    category: Optional[str] = Field(default="", description="Object category")


class AddObjectResponse(BaseModel):
    """Response after adding an object"""

    object_id: int = Field(..., description="Object ID")
    name: str = Field(..., description="Object name")
    category: str = Field(..., description="Object category")
    color: List[int] = Field(..., description="RGB color for visualization")
    frame_idx: int = Field(..., description="Frame where object was added")
    mask: str = Field(..., description="Base64 encoded mask for the initial frame")


# ============================================================
# Propagation
# ============================================================


class PropagateRequest(BaseModel):
    """Request to propagate masks across video"""

    session_id: str = Field(..., description="Session identifier")
    start_frame: Optional[int] = Field(
        default=None, description="Start frame for propagation"
    )
    end_frame: Optional[int] = Field(
        default=None, description="End frame for propagation"
    )
    direction: Optional[str] = Field(
        default="both",
        description="Propagation direction: 'forward', 'backward', or 'both'",
    )


class FrameMask(BaseModel):
    """Mask data for a single frame"""

    frame_idx: int = Field(..., description="Frame index")
    masks: Dict[int, str] = Field(
        ..., description="Object ID -> Base64 encoded mask mapping"
    )


class PropagateResponse(BaseModel):
    """Response after propagating masks"""

    session_id: str = Field(..., description="Session identifier")
    total_frames: int = Field(..., description="Total frames processed")
    frames: List[FrameMask] = Field(..., description="List of frame masks")


# ============================================================
# Mask Update
# ============================================================


class UpdateMaskRequest(BaseModel):
    """Request to update a mask with a custom edited mask"""

    session_id: str = Field(..., description="Session identifier")
    frame_idx: int = Field(..., description="Frame index")
    object_id: int = Field(..., description="Object ID to update")
    mask: str = Field(..., description="Base64 encoded mask (PNG format)")


class UpdateMaskResponse(BaseModel):
    """Response after updating a mask"""

    object_id: int = Field(..., description="Object ID")
    frame_idx: int = Field(..., description="Frame index")
    mask: str = Field(..., description="Base64 encoded updated mask")


# ============================================================
# Refinement
# ============================================================


class RefineRequest(BaseModel):
    """Request to refine a mask on a specific frame"""

    session_id: str = Field(..., description="Session identifier")
    frame_idx: int = Field(..., description="Frame index to refine")
    object_id: int = Field(..., description="Object ID to refine")
    points: List[List[float]] = Field(
        ..., description="List of [x, y] refinement points"
    )
    labels: List[int] = Field(..., description="Point labels (1=positive, 0=negative)")


class RefineResponse(BaseModel):
    """Response after refining a mask"""

    object_id: int = Field(..., description="Object ID")
    frame_idx: int = Field(..., description="Frame index")
    mask: str = Field(..., description="Base64 encoded refined mask")


# ============================================================
# Frame Masks
# ============================================================


class GetFrameMasksRequest(BaseModel):
    """Request to get masks for a specific frame"""

    session_id: str = Field(..., description="Session identifier")
    frame_idx: int = Field(..., description="Frame index")


class GetFrameMasksResponse(BaseModel):
    """Response with masks for a specific frame"""

    frame_idx: int = Field(..., description="Frame index")
    masks: Dict[int, str] = Field(
        ..., description="Object ID -> Base64 encoded mask mapping"
    )


# ============================================================
# Health & Status
# ============================================================


class HealthResponse(BaseModel):
    """Health check response"""

    message: str
    status: str
    model_loaded: bool
    timestamp: float
    active_sessions: Optional[int] = None


class ErrorResponse(BaseModel):
    """Error response"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error info")


# ============================================================
# Utility Functions
# ============================================================


def encode_mask(mask_array: np.ndarray) -> str:
    """Encode numpy mask array to base64 PNG string with validation"""
    import logging
    logger = logging.getLogger(__name__)

    # CRITICAL: Validate mask before encoding to prevent corrupted output
    if np.isnan(mask_array).any():
        logger.error("encode_mask: Mask contains NaN values! Returning empty mask.")
        mask_array = np.zeros_like(mask_array, dtype=np.uint8)

    if mask_array.size == 0:
        logger.error("encode_mask: Empty mask array! Creating default empty mask.")
        mask_array = np.zeros((480, 640), dtype=np.uint8)

    # Validate and clip mask values to valid range
    if mask_array.dtype != np.uint8:
        # Check range before conversion
        if mask_array.max() > 255 or mask_array.min() < 0:
            logger.warning(f"encode_mask: Mask has invalid range [{mask_array.min()}, {mask_array.max()}], clipping to [0, 255]")
            mask_array = np.clip(mask_array, 0, 255)
        mask_array = (mask_array * 255).astype(np.uint8)

    # Final validation: ensure uint8 mask is in valid range
    if mask_array.max() > 255 or mask_array.min() < 0:
        logger.warning(f"encode_mask: Final mask out of range, clipping")
        mask_array = np.clip(mask_array, 0, 255).astype(np.uint8)

    mask_image = Image.fromarray(mask_array, mode="L")
    buffer = io.BytesIO()
    mask_image.save(buffer, format="PNG", optimize=True)  # Add optimize=True for smaller size
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def decode_mask(mask_b64: str) -> np.ndarray:
    """Decode base64 PNG string to numpy mask array"""
    mask_bytes = base64.b64decode(mask_b64)
    mask_image = Image.open(io.BytesIO(mask_bytes))
    return np.array(mask_image)
