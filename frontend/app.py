import streamlit as st
import os
import sys
import numpy as np
import cv2
from PIL import Image
import tempfile

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import frontend components
from frontend.components.video_player import VideoPlayer
from frontend.components.canvas import AnnotationCanvas
from frontend.components.timeline import Timeline
from frontend.components.tools import AnnotationTools

# Import backend components (for MVP, we'll keep these simple)
from backend.core.sam_model import SAMModel
from backend.core.video_processor import VideoProcessor

# Set page configuration
st.set_page_config(layout="wide", page_title="SAM Video Segmentation Tool")

def main():
    st.title("Video Segmentation Tool with Segment Anything")
    
    # Sidebar for tools and settings
    with st.sidebar:
        st.header("Tools")
        tool_type = st.radio(
            "Select Tool",
            ("Point Prompt", "Box Prompt", "Clear Prompts")
        )
        
        st.header("Settings")
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7)
        
        st.header("Upload")
        uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov"])
    
    # Main area - split into columns
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.header("Video Canvas")
        
        if uploaded_file is not None:
            # Save the uploaded file to a temporary file
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(uploaded_file.read())
            video_path = tfile.name
            
            # Initialize video processor and SAM model
            video_processor = VideoProcessor(video_path)
            sam_model = SAMModel()
            
            # Get the first frame
            first_frame = video_processor.get_frame(0)
            
            # Display the canvas for annotation
            canvas_result = st.image(first_frame, caption="Video Frame")
            
            # Add a placeholder for segmentation results
            mask_placeholder = st.empty()
            
            # Simple frame selection for MVP
            frame_idx = st.slider("Frame", 0, video_processor.total_frames - 1, 0)
            current_frame = video_processor.get_frame(frame_idx)
            
            # Update the canvas with the selected frame
            canvas_result.image(current_frame, caption=f"Frame {frame_idx}")
            
            # Handle basic interaction (simulated for MVP)
            if st.button("Apply SAM"):
                # Simulate SAM processing
                # In a real app, we would use interactive canvas inputs
                mask = sam_model.predict(current_frame, prompt_type="center-point")
                
                # Create a visualization of the mask
                colored_mask = np.zeros_like(current_frame)
                colored_mask[:,:,1] = mask * 255  # Green channel
                
                # Blend original image with mask
                alpha = 0.7
                result = cv2.addWeighted(current_frame, alpha, colored_mask, 1-alpha, 0)
                
                # Display the result
                mask_placeholder.image(result, caption="Segmentation Result")
    
    with col2:
        st.header("Object Classes")
        classes = ["Person", "Vehicle", "Animal", "Furniture"]
        selected_class = st.selectbox("Select Class", classes)
        
        st.header("Annotations")
        st.write("Current annotations will appear here")
        
        # Export button
        if st.button("Export Annotations"):
            st.write("Exporting annotations (simulated)")
            st.success("Annotations exported successfully!")

if __name__ == "__main__":
    main()
