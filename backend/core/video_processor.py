import cv2
import numpy as np
import os

class VideoProcessor:
    """
    Video processing utilities for frame extraction
    """
    def __init__(self, video_path):
        """
        Initialize with a video file
        
        Args:
            video_path (str): Path to the video file
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        # Get video properties
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
    def get_frame(self, frame_idx):
        """
        Extract a specific frame from the video
        
        Args:
            frame_idx (int): Frame index
            
        Returns:
            numpy.ndarray: Frame as RGB image
        """
        if frame_idx < 0 or frame_idx >= self.total_frames:
            return None
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        
        if ret:
            # Convert from BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return frame
        return None
    
    def extract_keyframes(self, method="uniform", num_frames=10):
        """
        Extract keyframes from the video
        
        Args:
            method (str): Method for keyframe extraction ('uniform' or 'scene_change')
            num_frames (int): Number of frames to extract
            
        Returns:
            list: List of frame indices
        """
        if method == "uniform":
            # Uniformly sample frames
            if self.total_frames <= num_frames:
                return list(range(self.total_frames))
            
            indices = np.linspace(0, self.total_frames - 1, num_frames, dtype=int)
            return indices.tolist()
        
        elif method == "scene_change":
            # This would implement scene change detection
            # For MVP, we'll just return uniform sampling
            return self.extract_keyframes(method="uniform", num_frames=num_frames)
        
        return []
    
    def release(self):
        """Release the video capture resource"""
        if self.cap:
            self.cap.release()
