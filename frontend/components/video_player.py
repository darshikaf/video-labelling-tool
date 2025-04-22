import cv2
import numpy as np
import streamlit as st

class VideoPlayer:
    def __init__(self, video_path):
        """
        Initialize the video player with a video file
        
        Args:
            video_path (str): Path to the video file
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def get_frame(self, frame_idx):
        """
        Get a specific frame from the video
        
        Args:
            frame_idx (int): Frame index
            
        Returns:
            numpy.ndarray: Frame as image array
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
    
    def release(self):
        """Release the video capture resource"""
        if self.cap:
            self.cap.release()
