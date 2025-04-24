import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
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

            sam_model = SAMModel()
            # Save the uploaded file to a temporary file
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(uploaded_file.read())
            video_path = tfile.name

            # Initialize video processor
            video_processor = VideoProcessor(video_path)
            
            # Initialize SAM model
            # sam_model = SAMModel(model_type="vit_h", checkpoint="sam_vit_h_4b8939.pth")


            # Slider to select the frame
            frame_idx = st.slider("Frame", 0, video_processor.total_frames - 1, 0)
            current_frame = video_processor.get_frame(frame_idx)

            # Display the frame and get click coordinates
            clicked = streamlit_image_coordinates(
                current_frame,
                key="video_canvas"
            )

            # TODO-1001: put the feedback placeholder on top of the image created by streamlit_image_coordinates
            # Add a placeholder to show feedback after click
            feedback_placeholder = st.empty()

            if clicked:
                x, y = int(clicked['x']), int(clicked['y'])  # Convert to int for cv2.circle
                st.write(f"Clicked at coordinates: ({x}, {y})")
                
                # Visual feedback of the click
                feedback_image = current_frame.copy()
                cv2.circle(feedback_image, (x, y), 5, (0, 255, 0), -1)
                feedback_placeholder.image(feedback_image, caption="Click Position")

                # Add point to SAM model
                sam_model.add_point(x, y, label=1)
                # Run segmentation
                segmentation_result = sam_model.run_segmentation(current_frame)
                feedback_placeholder.write(f"Segmentation result: {segmentation_result}")


            else:
                feedback_placeholder.image(current_frame, caption=f"Frame {frame_idx}")



            
    
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
