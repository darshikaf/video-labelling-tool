"""
SAM 2 Video Segmentation Core Module

Provides video-based segmentation with temporal propagation using Meta's SAM 2.
"""

from .sam2_video_predictor import SAM2VideoPredictor, TrackedObject, VideoSession

__all__ = [
    "SAM2VideoPredictor",
    "VideoSession",
    "TrackedObject",
]
