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
from frontend.components.export import ExportInterface

# Import backend components (for MVP, we'll keep these simple)
from backend.core.sam_model import SAMModel
from backend.core.video_processor import VideoProcessor

# Set page configuration
st.set_page_config(layout="wide", page_title="SAM Video Segmentation Tool")

def main():
    # Initialize session state for storing click coordinates and masks
    if 'click_x' not in st.session_state:
        st.session_state.click_x = None
    if 'click_y' not in st.session_state:
        st.session_state.click_y = None
    if 'current_mask' not in st.session_state:
        st.session_state.current_mask = None
    if 'annotations' not in st.session_state:
        st.session_state.annotations = {"categories": [], "frames": {}}
        
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
    
    # Object Classes section (need to define this before video canvas to access selected_class)
    with col2:
        st.header("Object Classes")
        classes = ["Person", "Vehicle", "Animal", "Furniture"]
        
        # Add class management
        new_class = st.text_input("Add New Class")
        if st.button("Add Class") and new_class and new_class not in classes:
            classes.append(new_class)
            if new_class not in st.session_state.annotations["categories"]:
                st.session_state.annotations["categories"].append(new_class)
                
        selected_class = st.selectbox("Select Class", classes)
        if selected_class not in st.session_state.annotations["categories"]:
            st.session_state.annotations["categories"].append(selected_class)
    
    # Video Canvas section
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
            
            # Create a placeholder for the image
            image_placeholder = st.empty()
            
            # Display the current frame
            image_placeholder.image(current_frame, caption=f"Frame {frame_idx} - Click on an object")
            
            # Annotation controls - simplified structure without nested columns
            st.subheader("Annotation Controls")
            st.markdown("👆 Click on the image to place a point prompt")
            
            # Use simple sliders without nested columns
            click_x = st.slider("X Position", 0, video_processor.width-1, video_processor.width//2)
            click_y = st.slider("Y Position", 0, video_processor.height-1, video_processor.height//2)
            
            if st.button("Place Point"):
                st.session_state.click_x = click_x
                st.session_state.click_y = click_y
                
                # Generate mask from the clicked point
                mask = sam_model.predict(
                    current_frame, 
                    prompt_type="point", 
                    points=[(click_x, click_y, True)]
                )
                
                st.session_state.current_mask = mask
                
                # Create visualization
                colored_mask = np.zeros_like(current_frame)
                colored_mask[:,:,1] = mask * 255  # Green channel
                
                # Draw point on the image
                result = current_frame.copy()
                cv2.circle(result, (click_x, click_y), 5, (255, 0, 0), -1)
                
                # Blend original image with mask
                alpha = 0.7
                result = cv2.addWeighted(result, alpha, colored_mask, 1-alpha, 0)
                
                # Display the result
                image_placeholder.image(result, caption=f"Frame {frame_idx} with Segmentation")
                
                # Store annotation in session state
                if str(frame_idx) not in st.session_state.annotations["frames"]:
                    st.session_state.annotations["frames"][str(frame_idx)] = []
                
                # Add the annotation
                st.session_state.annotations["frames"][str(frame_idx)].append({
                    "category": selected_class,
                    "mask": mask,
                    "points": [(click_x, click_y, True)]
                })
            
            # Prompt info section
            st.subheader("Prompt Info")
            if st.session_state.click_x is not None:
                st.write(f"Last click: ({st.session_state.click_x}, {st.session_state.click_y})")
            
            if st.session_state.current_mask is not None:
                mask_area = np.sum(st.session_state.current_mask)
                st.write(f"Mask area: {mask_area} pixels")
                
            if st.button("Clear"):
                st.session_state.click_x = None
                st.session_state.click_y = None
                st.session_state.current_mask = None
                image_placeholder.image(current_frame, caption=f"Frame {frame_idx}")
    
    # Continue with the Annotations section in col2
    with col2:
        st.header("Annotations")
        if st.session_state.annotations["frames"]:
            st.write(f"Frames annotated: {len(st.session_state.annotations['frames'])}")
            total_annotations = sum(len(annotations) for annotations in st.session_state.annotations["frames"].values())
            st.write(f"Total annotations: {total_annotations}")
            
            # Show annotations for current frame
            if str(frame_idx) in st.session_state.annotations["frames"]:
                st.write(f"Annotations for frame {frame_idx}:")
                for i, anno in enumerate(st.session_state.annotations["frames"][str(frame_idx)]):
                    st.write(f"  {i+1}. {anno['category']}")
        else:
            st.write("No annotations yet. Click on objects in the video to annotate them.")
        
        # Export interface
        export_interface = ExportInterface()
        export_config = export_interface.render_export_ui()
        
        if st.button("Export Annotations"):
            if uploaded_file is not None and st.session_state.annotations["frames"]:
                # Collect frame information
                frames = {}
                for frame_str in st.session_state.annotations["frames"]:
                    frames[frame_str] = {
                        "width": video_processor.width,
                        "height": video_processor.height
                    }
                    
                # Export
                export_path = export_interface.export_annotations(
                    uploaded_file.name,
                    frames,
                    st.session_state.annotations,
                    export_format=export_config["format"],
                    export_dir=export_config["directory"]
                )
                
                st.success(f"Annotations exported successfully to {export_path}")
            else:
                st.error("Please upload a video and create annotations first")

if __name__ == "__main__":
    main()
