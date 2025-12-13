"""
SAM 2 Video Predictor

This module provides video-based segmentation using Meta's SAM 2 model.
Unlike the original SAM which works frame-by-frame, SAM 2 propagates
masks temporally across video frames with a memory mechanism.
"""

import logging
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    """Represents a tracked object in a video session"""

    object_id: int
    name: str = ""
    category: str = ""
    color: Tuple[int, int, int] = (255, 0, 0)  # RGB
    prompts: List[Dict[str, Any]] = field(default_factory=list)
    masks: Dict[int, np.ndarray] = field(default_factory=dict)  # frame_idx -> mask


@dataclass
class VideoSession:
    """Represents an active video annotation session"""

    session_id: str
    video_path: str
    video_frames: List[np.ndarray]  # All frames loaded in memory
    frame_width: int
    frame_height: int
    total_frames: int
    fps: float
    frames_dir: Optional[str] = None  # Temp dir with extracted frames for SAM 2
    objects: Dict[int, TrackedObject] = field(default_factory=dict)
    inference_state: Any = None  # SAM 2 inference state
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    def update_access_time(self):
        self.last_accessed = time.time()

    @property
    def idle_time(self) -> float:
        return time.time() - self.last_accessed

    def cleanup(self):
        """Clean up temporary files"""
        if self.frames_dir and os.path.exists(self.frames_dir):
            shutil.rmtree(self.frames_dir, ignore_errors=True)


class SAM2VideoPredictor:
    """
    SAM 2 Video Predictor for temporal mask propagation.

    This class manages video annotation sessions where users can:
    1. Initialize a session with a video
    2. Add objects by clicking on specific frames
    3. Propagate masks to all frames automatically
    4. Refine masks on specific frames
    """

    # Model checkpoint configurations
    MODEL_CONFIGS = {
        "tiny": {
            "config": "sam2_hiera_t.yaml",
            "checkpoint": "sam2_hiera_tiny.pt",
            "url": "https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_tiny.pt",
        },
        "small": {
            "config": "sam2_hiera_s.yaml",
            "checkpoint": "sam2_hiera_small.pt",
            "url": "https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_small.pt",
        },
        "base_plus": {
            "config": "sam2_hiera_b+.yaml",
            "checkpoint": "sam2_hiera_base_plus.pt",
            "url": "https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_base_plus.pt",
        },
        "large": {
            "config": "sam2_hiera_l.yaml",
            "checkpoint": "sam2_hiera_large.pt",
            "url": "https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_large.pt",
        },
    }

    # Default colors for objects (RGB)
    OBJECT_COLORS = [
        (255, 0, 0),  # Red
        (0, 255, 0),  # Green
        (0, 0, 255),  # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
        (255, 128, 0),  # Orange
        (128, 0, 255),  # Purple
    ]

    def __init__(
        self,
        model_size: str = "base_plus",
        model_dir: str = "/app/models",
        device: str = "auto",
        session_timeout: int = 300,  # 5 minutes (reduced from 30)
        max_concurrent_sessions: int = 2,  # Limit concurrent sessions
        max_video_frames: int = 300,  # Max frames to prevent memory issues (~10s at 30fps)
        max_frame_dimension: int = 1920,  # Max width/height to prevent huge videos
    ):
        self.model_size = model_size
        self.model_dir = Path(model_dir)
        self.session_timeout = session_timeout
        self.max_concurrent_sessions = max_concurrent_sessions
        self.max_video_frames = max_video_frames
        self.max_frame_dimension = max_frame_dimension

        # Determine device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        logger.info(f"Using device: {self.device}")
        logger.info(f"Max concurrent sessions: {self.max_concurrent_sessions}")
        logger.info(f"Max video frames: {self.max_video_frames}")
        logger.info(f"Session timeout: {self.session_timeout}s")

        # SAM 2 model components
        self.predictor = None
        self._model_loaded = False

        # Active sessions
        self.sessions: Dict[str, VideoSession] = {}

    async def initialize(self):
        """Initialize the SAM 2 model"""
        try:
            await self._load_model()
            self._model_loaded = True
            logger.info("SAM 2 model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SAM 2 model: {e}")
            raise

    async def _load_model(self):
        """Load the SAM 2 model checkpoint"""
        from sam2.build_sam import build_sam2_video_predictor

        model_cfg = self.MODEL_CONFIGS[self.model_size]
        checkpoint_path = self.model_dir / model_cfg["checkpoint"]

        # Download checkpoint if not present
        if not checkpoint_path.exists():
            await self._download_checkpoint(model_cfg)

        logger.info(f"Loading SAM 2 {self.model_size} model from {checkpoint_path}")

        # Build the video predictor
        self.predictor = build_sam2_video_predictor(
            config_file=model_cfg["config"],
            ckpt_path=str(checkpoint_path),
            device=self.device,
        )

        logger.info("SAM 2 video predictor loaded successfully")

    async def _download_checkpoint(self, model_cfg: Dict[str, str]):
        """Download model checkpoint if not present"""
        import urllib.request

        checkpoint_path = self.model_dir / model_cfg["checkpoint"]
        self.model_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading SAM 2 checkpoint to {checkpoint_path}...")

        url = model_cfg["url"]
        try:
            urllib.request.urlretrieve(url, str(checkpoint_path))
            logger.info("Checkpoint downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download checkpoint: {e}")
            raise

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded

    # Session Management

    def create_session(self, video_path: str) -> VideoSession:
        """
        Create a new video annotation session.

        Args:
            video_path: Path to the video file

        Returns:
            VideoSession object with session details
        """
        # Check session limit to prevent resource exhaustion
        if len(self.sessions) >= self.max_concurrent_sessions:
            # Auto-cleanup old sessions to make room
            cleaned = self.cleanup_expired_sessions()
            if len(self.sessions) >= self.max_concurrent_sessions:
                raise RuntimeError(
                    f"Maximum concurrent sessions ({self.max_concurrent_sessions}) reached. "
                    f"Please close existing sessions or wait for them to expire."
                )
            logger.info(f"Auto-cleaned {cleaned} expired sessions to make room")

        session_id = str(uuid.uuid4())

        # Load video frames with safety limits
        frames, metadata = self._load_video_frames(video_path)

        # Extract frames to temp directory for SAM 2 (it needs JPEG folder or MP4)
        frames_dir = self._extract_frames_to_dir(frames, session_id)

        # Create session
        session = VideoSession(
            session_id=session_id,
            video_path=video_path,
            video_frames=frames,
            frame_width=metadata["width"],
            frame_height=metadata["height"],
            total_frames=len(frames),
            fps=metadata["fps"],
            frames_dir=frames_dir,
        )

        # Initialize SAM 2 inference state for this video
        if self.predictor is not None:
            # Use the extracted frames directory instead of the video file
            session.inference_state = self.predictor.init_state(video_path=frames_dir)

        self.sessions[session_id] = session
        logger.info(
            f"Created session {session_id} for video {video_path} ({len(frames)} frames)"
        )

        return session

    def _extract_frames_to_dir(self, frames: List[np.ndarray], session_id: str) -> str:
        """Extract video frames to a temp directory as JPEGs for SAM 2"""
        # Create temp directory
        frames_dir = tempfile.mkdtemp(prefix=f"sam2_frames_{session_id}_")

        logger.info(f"Extracting {len(frames)} frames to {frames_dir}")

        for i, frame in enumerate(frames):
            # SAM 2 expects frames named as sequential integers with leading zeros
            frame_path = os.path.join(frames_dir, f"{i:06d}.jpg")
            # Convert RGB to BGR for cv2.imwrite
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(frame_path, frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])

        logger.info(f"Extracted {len(frames)} frames to {frames_dir}")
        return frames_dir

    def get_session(self, session_id: str) -> Optional[VideoSession]:
        """Get an existing session by ID"""
        session = self.sessions.get(session_id)
        if session:
            session.update_access_time()
        return session

    def close_session(self, session_id: str):
        """Close and cleanup a session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]

            # Reset the inference state to free GPU memory
            if session.inference_state is not None and self.predictor is not None:
                self.predictor.reset_state(session.inference_state)

            # Clean up temp files
            session.cleanup()

            # Remove from active sessions
            del self.sessions[session_id]
            logger.info(f"Closed session {session_id}")

    def cleanup_expired_sessions(self):
        """Remove sessions that have been idle for too long"""
        expired = [
            sid
            for sid, session in self.sessions.items()
            if session.idle_time > self.session_timeout
        ]
        for sid in expired:
            logger.info(
                f"Session {sid} expired (idle for {self.sessions[sid].idle_time:.0f}s)"
            )
            self.close_session(sid)
        return len(expired)

    def _load_video_frames(
        self, video_path: str
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """Load video frames with safety limits to prevent memory exhaustion"""
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Check frame dimensions
        if width > self.max_frame_dimension or height > self.max_frame_dimension:
            cap.release()
            raise ValueError(
                f"Video dimensions ({width}x{height}) exceed maximum allowed "
                f"({self.max_frame_dimension}x{self.max_frame_dimension}). "
                f"Please use a lower resolution video."
            )

        # Check frame count
        if total_frames_in_video > self.max_video_frames:
            cap.release()
            raise ValueError(
                f"Video has {total_frames_in_video} frames, which exceeds "
                f"maximum allowed ({self.max_video_frames}). "
                f"Please use a shorter video clip or increase max_video_frames."
            )

        frames = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Additional safety check during loading
            if frame_count >= self.max_video_frames:
                logger.warning(
                    f"Stopped loading at {frame_count} frames (limit: {self.max_video_frames})"
                )
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
            frame_count += 1

        cap.release()

        metadata = {
            "fps": fps,
            "width": width,
            "height": height,
            "total_frames": len(frames),
        }

        logger.info(
            f"Loaded {len(frames)} frames from {video_path} ({width}x{height} @ {fps}fps)"
        )

        return frames, metadata

    # Object Tracking

    def add_object(
        self,
        session_id: str,
        frame_idx: int,
        object_id: int,
        points: List[Tuple[float, float]],
        labels: List[int],
        name: str = "",
        category: str = "",
    ) -> Dict[str, Any]:
        """
        Add an object to track by providing point prompts on a specific frame.

        Args:
            session_id: Session ID
            frame_idx: Frame index where the object is visible
            object_id: Unique ID for this object
            points: List of (x, y) coordinates
            labels: List of labels (1 for positive/include, 0 for negative/exclude)
            name: Optional name for the object (e.g., "Forceps")
            category: Optional category (e.g., "Instrument")

        Returns:
            Dictionary with object info and initial mask
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if frame_idx < 0 or frame_idx >= session.total_frames:
            raise ValueError(f"Invalid frame index: {frame_idx}")

        # Create tracked object
        color_idx = len(session.objects) % len(self.OBJECT_COLORS)
        tracked_object = TrackedObject(
            object_id=object_id,
            name=name or f"Object {object_id}",
            category=category,
            color=self.OBJECT_COLORS[color_idx],
            prompts=[
                {
                    "frame_idx": frame_idx,
                    "points": points,
                    "labels": labels,
                    "type": "initial",
                }
            ],
        )

        # Convert points to numpy arrays for SAM 2
        points_np = np.array(points, dtype=np.float32)
        labels_np = np.array(labels, dtype=np.int32)

        # Add to SAM 2 inference state
        if self.predictor is not None and session.inference_state is not None:
            # Add object with point prompts
            _, out_obj_ids, out_mask_logits = self.predictor.add_new_points_or_box(
                inference_state=session.inference_state,
                frame_idx=frame_idx,
                obj_id=object_id,
                points=points_np,
                labels=labels_np,
            )

            # Convert logits to binary mask
            mask = (out_mask_logits[0] > 0.0).cpu().numpy().squeeze().astype(np.uint8)
            tracked_object.masks[frame_idx] = mask
        else:
            # Simulation mode - create simple circular mask
            mask = self._simulate_mask(session, points, labels)
            tracked_object.masks[frame_idx] = mask

        session.objects[object_id] = tracked_object

        return {
            "object_id": object_id,
            "name": tracked_object.name,
            "category": tracked_object.category,
            "color": tracked_object.color,
            "frame_idx": frame_idx,
            "mask": mask,
        }

    def add_object_with_box(
        self,
        session_id: str,
        frame_idx: int,
        object_id: int,
        box: Tuple[float, float, float, float],  # x1, y1, x2, y2
        name: str = "",
        category: str = "",
    ) -> Dict[str, Any]:
        """
        Add an object to track by providing a bounding box on a specific frame.

        Args:
            session_id: Session ID
            frame_idx: Frame index where the object is visible
            object_id: Unique ID for this object
            box: Bounding box as (x1, y1, x2, y2)
            name: Optional name for the object
            category: Optional category

        Returns:
            Dictionary with object info and initial mask
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if frame_idx < 0 or frame_idx >= session.total_frames:
            raise ValueError(f"Invalid frame index: {frame_idx}")

        # Create tracked object
        color_idx = len(session.objects) % len(self.OBJECT_COLORS)
        tracked_object = TrackedObject(
            object_id=object_id,
            name=name or f"Object {object_id}",
            category=category,
            color=self.OBJECT_COLORS[color_idx],
            prompts=[{"frame_idx": frame_idx, "box": box, "type": "initial_box"}],
        )

        # Convert box to numpy array for SAM 2
        box_np = np.array(box, dtype=np.float32)

        # Add to SAM 2 inference state
        if self.predictor is not None and session.inference_state is not None:
            _, out_obj_ids, out_mask_logits = self.predictor.add_new_points_or_box(
                inference_state=session.inference_state,
                frame_idx=frame_idx,
                obj_id=object_id,
                box=box_np,
            )

            mask = (out_mask_logits[0] > 0.0).cpu().numpy().squeeze().astype(np.uint8)
            tracked_object.masks[frame_idx] = mask
        else:
            # Simulation mode
            mask = self._simulate_box_mask(session, box)
            tracked_object.masks[frame_idx] = mask

        session.objects[object_id] = tracked_object

        return {
            "object_id": object_id,
            "name": tracked_object.name,
            "category": tracked_object.category,
            "color": tracked_object.color,
            "frame_idx": frame_idx,
            "mask": mask,
        }

    def propagate_masks(
        self,
        session_id: str,
        start_frame: Optional[int] = None,
        end_frame: Optional[int] = None,
        direction: str = "both",  # "forward", "backward", or "both"
    ) -> Dict[str, Any]:
        """
        Propagate masks from annotated frames to all other frames.

        Args:
            session_id: Session ID
            start_frame: Optional start frame (default: 0)
            end_frame: Optional end frame (default: last frame)
            direction: Propagation direction

        Returns:
            Dictionary with all frame masks for all objects
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if not session.objects:
            raise ValueError("No objects to propagate")

        start_frame = start_frame or 0
        end_frame = end_frame or session.total_frames - 1

        results = {
            "session_id": session_id,
            "total_frames": session.total_frames,
            "frames": {},
        }

        if self.predictor is not None and session.inference_state is not None:
            # Use SAM 2's video propagation
            video_segments = {}

            logger.info(
                f"Starting mask propagation for session {session_id} "
                f"({session.total_frames} frames, {len(session.objects)} objects)"
            )
            start_time = time.time()
            frame_count = 0

            for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
            ) in self.predictor.propagate_in_video(
                inference_state=session.inference_state
            ):
                # Store masks for each object in this frame
                frame_masks = {}
                for i, obj_id in enumerate(out_obj_ids):
                    mask = (
                        (out_mask_logits[i] > 0.0)
                        .cpu()
                        .numpy()
                        .squeeze()
                        .astype(np.uint8)
                    )

                    # Update the tracked object's masks
                    if obj_id in session.objects:
                        session.objects[obj_id].masks[out_frame_idx] = mask

                    frame_masks[int(obj_id)] = mask

                video_segments[out_frame_idx] = frame_masks
                frame_count += 1

                # Log progress every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"Propagation progress: {frame_count}/{session.total_frames} frames "
                        f"({fps:.1f} fps)"
                    )

            elapsed = time.time() - start_time
            logger.info(
                f"Mask propagation completed for session {session_id}: "
                f"{frame_count} frames in {elapsed:.2f}s "
                f"({frame_count/elapsed:.1f} fps)"
            )

            results["frames"] = video_segments
        else:
            # Simulation mode - propagate with simple motion estimation
            results["frames"] = self._simulate_propagation(session)

        return results

    def refine_mask(
        self,
        session_id: str,
        frame_idx: int,
        object_id: int,
        points: List[Tuple[float, float]],
        labels: List[int],
    ) -> Dict[str, Any]:
        """
        Add refinement points to an existing object on a specific frame.

        This is used to correct mask drift on frames where the propagated
        mask is inaccurate.

        Args:
            session_id: Session ID
            frame_idx: Frame index to refine
            object_id: Object ID to refine
            points: List of (x, y) refinement points
            labels: List of labels (1 for positive, 0 for negative)

        Returns:
            Dictionary with updated mask
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if object_id not in session.objects:
            raise ValueError(f"Object not found: {object_id}")

        tracked_object = session.objects[object_id]

        # Record the refinement
        tracked_object.prompts.append(
            {
                "frame_idx": frame_idx,
                "points": points,
                "labels": labels,
                "type": "refinement",
            }
        )

        # Convert to numpy
        points_np = np.array(points, dtype=np.float32)
        labels_np = np.array(labels, dtype=np.int32)

        # Add refinement to SAM 2
        if self.predictor is not None and session.inference_state is not None:
            _, out_obj_ids, out_mask_logits = self.predictor.add_new_points_or_box(
                inference_state=session.inference_state,
                frame_idx=frame_idx,
                obj_id=object_id,
                points=points_np,
                labels=labels_np,
            )

            mask = (out_mask_logits[0] > 0.0).cpu().numpy().squeeze().astype(np.uint8)
            tracked_object.masks[frame_idx] = mask
        else:
            # Update simulation
            existing_mask = tracked_object.masks.get(
                frame_idx,
                np.zeros((session.frame_height, session.frame_width), dtype=np.uint8),
            )
            mask = self._apply_refinement_simulation(existing_mask, points, labels)
            tracked_object.masks[frame_idx] = mask

        return {"object_id": object_id, "frame_idx": frame_idx, "mask": mask}

    def get_frame_masks(self, session_id: str, frame_idx: int) -> Dict[int, np.ndarray]:
        """Get all object masks for a specific frame"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        frame_masks = {}
        for obj_id, obj in session.objects.items():
            if frame_idx in obj.masks:
                frame_masks[obj_id] = obj.masks[frame_idx]

        return frame_masks

    def get_all_masks(self, session_id: str) -> Dict[int, Dict[int, np.ndarray]]:
        """Get all masks for all frames and objects"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        all_masks = {}
        for obj_id, obj in session.objects.items():
            all_masks[obj_id] = obj.masks.copy()

        return all_masks

    # Simulation methods for development/testing without GPU

    def _simulate_mask(
        self,
        session: VideoSession,
        points: List[Tuple[float, float]],
        labels: List[int],
    ) -> np.ndarray:
        """Simulate mask generation for testing"""
        mask = np.zeros((session.frame_height, session.frame_width), dtype=np.uint8)

        for point, label in zip(points, labels):
            x, y = int(point[0]), int(point[1])
            radius = min(session.frame_height, session.frame_width) // 10

            if label == 1:  # Positive point
                cv2.circle(mask, (x, y), radius, 1, -1)
            else:  # Negative point
                cv2.circle(mask, (x, y), radius, 0, -1)

        return mask

    def _simulate_box_mask(
        self, session: VideoSession, box: Tuple[float, float, float, float]
    ) -> np.ndarray:
        """Simulate box mask for testing"""
        mask = np.zeros((session.frame_height, session.frame_width), dtype=np.uint8)
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(mask, (x1, y1), (x2, y2), 1, -1)
        return mask

    def _simulate_propagation(
        self, session: VideoSession
    ) -> Dict[int, Dict[int, np.ndarray]]:
        """Simulate mask propagation for testing"""
        results = {}

        for frame_idx in range(session.total_frames):
            frame_masks = {}
            for obj_id, obj in session.objects.items():
                # Find nearest annotated frame
                annotated_frames = list(obj.masks.keys())
                if not annotated_frames:
                    continue

                nearest_frame = min(annotated_frames, key=lambda f: abs(f - frame_idx))
                base_mask = obj.masks[nearest_frame]

                # Add slight random shift for simulation
                shift = (frame_idx - nearest_frame) * 2  # 2 pixels per frame
                if shift != 0:
                    M = np.float32([[1, 0, shift], [0, 1, 0]])
                    propagated_mask = cv2.warpAffine(
                        base_mask, M, (session.frame_width, session.frame_height)
                    )
                else:
                    propagated_mask = base_mask.copy()

                frame_masks[obj_id] = propagated_mask
                obj.masks[frame_idx] = propagated_mask

            results[frame_idx] = frame_masks

        return results

    def _apply_refinement_simulation(
        self, mask: np.ndarray, points: List[Tuple[float, float]], labels: List[int]
    ) -> np.ndarray:
        """Apply refinement points to an existing mask in simulation mode"""
        refined_mask = mask.copy()
        h, w = mask.shape

        for point, label in zip(points, labels):
            x, y = int(point[0]), int(point[1])
            radius = min(h, w) // 15

            if label == 1:  # Add to mask
                cv2.circle(refined_mask, (x, y), radius, 1, -1)
            else:  # Remove from mask
                cv2.circle(refined_mask, (x, y), radius, 0, -1)

        return refined_mask
