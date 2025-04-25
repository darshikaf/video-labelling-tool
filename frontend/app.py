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
    
    # Initialize session state to store points
    if 'points' not in st.session_state:
        st.session_state.points = []
    
    # Sidebar for tools and settings
    with st.sidebar:
        st.header("Tools")
        tool_type = st.radio(
            "Select Tool",
            ("Point Prompt", "Box Prompt", "Clear Prompts")
        )
        
        # Add point mode selection
        if tool_type == "Point Prompt":
            point_mode = st.radio("Point Type", ("Positive", "Negative"))
            is_positive = point_mode == "Positive"
        
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
            
            # Simple frame selection for MVP
            frame_idx = st.slider("Frame", 0, video_processor.total_frames - 1, 0)
            current_frame = video_processor.get_frame(frame_idx)
            
            # Get dimensions of the current frame for coordinate input validation
            frame_height, frame_width = current_frame.shape[:2]
            
            # Create a canvas to draw annotations
            canvas = AnnotationCanvas(frame_width, frame_height)
            
            # Add points from session state to canvas
            for x, y, is_pos in st.session_state.points:
                canvas.add_point(x, y, is_pos)
            
            # Draw annotations on the frame
            annotated_frame = canvas.draw_annotations(current_frame)
            
            # Display the canvas with annotations
            canvas_result = st.image(annotated_frame, caption=f"Frame {frame_idx}")
            
            # Add coordinate input for points
            st.subheader("Add Point")
            col_x, col_y = st.columns(2)
            with col_x:
                x_coord = st.number_input("X coordinate", min_value=0, max_value=frame_width-1, value=frame_width//2)
            with col_y:
                y_coord = st.number_input("Y coordinate", min_value=0, max_value=frame_height-1, value=frame_height//2)
            
            # Add point button
            if st.button("Add Point"):
                if tool_type == "Point Prompt":
                    st.session_state.points.append((x_coord, y_coord, is_positive))
                    # Update canvas with new point
                    canvas.add_point(x_coord, y_coord, is_positive)
                    # Redraw the frame with new annotation
                    annotated_frame = canvas.draw_annotations(current_frame)
                    canvas_result.image(annotated_frame, caption=f"Frame {frame_idx}")
            
            # Clear points button
            if st.button("Clear Points") or tool_type == "Clear Prompts":
                st.session_state.points = []
                canvas.clear()
                annotated_frame = canvas.draw_annotations(current_frame)
                canvas_result.image(annotated_frame, caption=f"Frame {frame_idx}")
            
            # Add a placeholder for segmentation results
            mask_placeholder = st.empty()
            
            # Apply SAM button
            if st.button("Apply SAM"):
                if st.session_state.points:
                    # Use points as input for SAM model
                    mask = sam_model.predict(current_frame, prompt_type="point", points=st.session_state.points)
                else:
                    # Fallback to center-point if no points added
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
        
        st.header("Points")
        # Show the current list of points
        if st.session_state.points:
            for i, (x, y, is_pos) in enumerate(st.session_state.points):
                point_type = "Positive" if is_pos else "Negative"
                st.write(f"Point {i+1}: ({x}, {y}) - {point_type}")
        else:
            st.write("No points added. Add points to create masks.")
        
        st.header("Annotations")
        st.write("Current annotations will appear here")
        
        # Export button
        if st.button("Export Annotations"):
            st.write("Exporting annotations (simulated)")
            st.success("Annotations exported successfully!")

if __name__ == "__main__":
    main()
