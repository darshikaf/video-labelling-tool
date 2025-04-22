import streamlit as st

class Timeline:
    def __init__(self, total_frames, fps):
        """
        Initialize the timeline controller
        
        Args:
            total_frames (int): Total number of frames
            fps (float): Frames per second
        """
        self.total_frames = total_frames
        self.fps = fps
        self.current_frame = 0
        
    def seek(self, frame_idx):
        """
        Seek to a specific frame
        
        Args:
            frame_idx (int): Frame index to seek to
            
        Returns:
            int: New current frame index
        """
        if 0 <= frame_idx < self.total_frames:
            self.current_frame = frame_idx
        return self.current_frame
    
    def next_frame(self):
        """Move to the next frame"""
        return self.seek(self.current_frame + 1)
    
    def prev_frame(self):
        """Move to the previous frame"""
        return self.seek(self.current_frame - 1)
    
    def frame_to_time(self, frame_idx):
        """Convert frame index to timestamp"""
        seconds = frame_idx / self.fps
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:05.2f}"
