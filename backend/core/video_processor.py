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
        
        # Store current frame buffer
        self.frame_buffer = {}
        self.buffer_size = 10  # Keep last 10 frames in memory
    
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
            
        # Check if frame is in buffer
        if frame_idx in self.frame_buffer:
            return self.frame_buffer[frame_idx]
            
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        
        if ret:
            # Convert from BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Add to buffer
            self.frame_buffer[frame_idx] = frame
            
            # Remove oldest frames if buffer is too large
            if len(self.frame_buffer) > self.buffer_size:
                oldest_key = min(self.frame_buffer.keys())
                del self.frame_buffer[oldest_key]
                
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
            # Scene change detection using OpenCV
            indices = []
            prev_frame = None
            
            # Create frame difference threshold
            threshold = 30.0
            
            # Set video to start
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Calculate step size to sample from the video
            step = max(1, self.total_frames // (num_frames * 10))
            
            for i in range(0, self.total_frames, step):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = self.cap.read()
                
                if not ret:
                    break
                    
                # Convert to grayscale for faster comparison
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(gray, prev_frame)
                    score = np.mean(diff)
                    
                    if score > threshold and len(indices) < num_frames:
                        indices.append(i)
                
                prev_frame = gray
            
            # If we didn't find enough scene changes, add some uniform samples
            if len(indices) < num_frames:
                remaining = num_frames - len(indices)
                uniform_samples = self.extract_keyframes(method="uniform", num_frames=remaining)
                
                # Filter out any duplicates or near-duplicates
                for sample in uniform_samples:
                    if not any(abs(sample - idx) < 10 for idx in indices):
                        indices.append(sample)
                        if len(indices) >= num_frames:
                            break
            
            return sorted(indices)
        
        return []
    
    def release(self):
        """Release the video capture resource"""
        if self.cap:
            self.cap.release()
