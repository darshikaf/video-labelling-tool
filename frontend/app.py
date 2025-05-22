import streamlit as st
import os
import sys
import numpy as np
import cv2
from PIL import Image
import tempfile
import streamlit_image_coordinates 

from pathlib import Path
# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import frontend components
from frontend.components.video_player import VideoPlayer
from frontend.components.canvas import AnnotationCanvas
from frontend.components.timeline import Timeline
from frontend.components.tools import AnnotationTools
from frontend.components.export import ExportInterface

# Import backend components
from backend.core.sam_model import SAMModel
from backend.core.video_processor import VideoProcessor

# Set page configuration
st.set_page_config(layout="wide", page_title="SAM Video Segmentation Tool")

# Define fixed canvas dimensions for consistency
CANVAS_WIDTH = 640
CANVAS_HEIGHT = 480

def resize_frame(frame, target_width=CANVAS_WIDTH, target_height=CANVAS_HEIGHT):
    """
    Resize frame to target dimensions while maintaining aspect ratio
    
    Args:
        frame (numpy.ndarray): Input frame
        target_width (int): Target width
        target_height (int): Target height
        
    Returns:
        numpy.ndarray: Resized frame
    """
    if frame is None:
        return None
        
    h, w = frame.shape[:2]
    
    # Calculate target dimensions while maintaining aspect ratio
    if w/h > target_width/target_height:
        # Width is the limiting factor
        new_w = target_width
        new_h = int(h * (target_width / w))
    else:
        # Height is the limiting factor
        new_h = target_height
        new_w = int(w * (target_height / h))
    
    # Resize the image
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Create a canvas of target size
    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    
    # Calculate position to paste (center the image)
    y_offset = (target_height - new_h) // 2
    x_offset = (target_width - new_w) // 2
    
    # Paste the resized image
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
    
    return canvas

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
    if 'selected_class' not in st.session_state:
        st.session_state.selected_class = "Person"  # TODO: Update default value
    
    # Initialize frame_idx with default value to avoid UnboundLocalError
    frame_idx = 0
    
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

    # Object Classes section
    with col2:
        st.header("Object Classes")
        classes = ["Person", "Vehicle", "Animal", "Furniture"] # TODO: update classes
        
        # Add class management
        new_class = st.text_input("Add New Class")
        if st.button("Add Class") and new_class and new_class not in classes:
            classes.append(new_class)
            if new_class not in st.session_state.annotations["categories"]:
                st.session_state.annotations["categories"].append(new_class)
                
        # Store selected class in session state with key parameter
        selected_class = st.selectbox("Select Class", classes, key="selected_class")
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
            
            # Get and resize frame
            original_frame = video_processor.get_frame(frame_idx)
            if original_frame is None:
                st.error("Could not read frame from video")
                return
                
            # Resize frame to match canvas dimensions
            current_frame = resize_frame(original_frame, CANVAS_WIDTH, CANVAS_HEIGHT)
            
            # Display instructions
            st.write("👆 **Click on the image to place a point prompt**")
            
            # Display the image with click detection
            coordinates = streamlit_image_coordinates.streamlit_image_coordinates(
                current_frame,
                key=f"frame_image_{frame_idx}"
            )
            
            # Process click if coordinates are received
            if coordinates:
                click_x = coordinates['x']
                click_y = coordinates['y']
                
                st.session_state.click_x = click_x
                st.session_state.click_y = click_y
                
                # Generate mask from the clicked point
                results = sam_model.predict(
                    points=[(click_x, click_y)],
                    labels=[1],  # 1 for foreground
                    image_frame=current_frame
                )
                
                mask_tensor = results[0].masks.data  # This is likely a tensor of shape (1, H, W)
                if hasattr(mask_tensor, "cpu"):
                    mask_np = mask_tensor.cpu().numpy()
                else:
                    mask_np = np.array(mask_tensor)
                # If mask_np has shape (1, H, W), squeeze it
                if mask_np.ndim == 3 and mask_np.shape[0] == 1:
                    mask_np = mask_np[0]
                mask_np = (mask_np * 255).astype("uint8")

                st.session_state.current_mask = mask_np

                # Create visualization
                colored_mask = np.zeros_like(current_frame)
                colored_mask[:,:,1] = mask_np  # Green channel
                
                # Draw point on the image
                result = current_frame.copy()
                cv2.circle(result, (click_x, click_y), 5, (255, 0, 0), -1)
                
                # Blend original image with mask
                alpha = 0.7
                result = cv2.addWeighted(result, alpha, colored_mask, 1-alpha, 0)
                
                # Display the result
                st.image(result, caption=f"Frame {frame_idx} with Segmentation")
                
                # # Store annotation in session state
                # if str(frame_idx) not in st.session_state.annotations["frames"]:
                #     st.session_state.annotations["frames"][str(frame_idx)] = []
                
                # # Add the annotation
                # st.session_state.annotations["frames"][str(frame_idx)].append({
                #     "category": st.session_state.selected_class,  # Use session state here
                #     "mask": mask,
                #     "points": [(click_x, click_y, True)]
                # })
                
                # Show point info below the image
                st.write(f"Point added: ({click_x}, {click_y})")
                
                # if mask is not None:
                #     mask_area = np.sum(mask)
                #     st.write(f"Mask area: {mask_area} pixels")
            if st.button("save results"):
                temp_path_name = Path(__file__).parent.parent / "input" / "temp_vid_image.jpg" 
                sam_model.save_yolo_labels(image_path=temp_path_name,
                                           image_frame=current_frame,
                                           video_frame_number=frame_idx,
                                           sam_results=results,
                                           label=1)
                st.success("Results saved successfully!")
            # Add a clear button
            if st.button("Clear Annotations"):
                pass
                # if str(frame_idx) in st.session_state.annotations["frames"]:
                #     st.session_state.annotations["frames"][str(frame_idx)] = []
                # st.session_state.current_mask = None
                # st.experimental_rerun()
            
        # Continue with the Annotations section
        # st.header("Annotations")
        # if st.session_state.annotations["frames"]:
        #     st.write(f"Frames annotated: {len(st.session_state.annotations['frames'])}")
        #     total_annotations = sum(len(annotations) for annotations in st.session_state.annotations["frames"].values())
        #     st.write(f"Total annotations: {total_annotations}")
            
        #     # Show annotations for current frame
        #     if str(frame_idx) in st.session_state.annotations["frames"]:
        #         st.write(f"Annotations for frame {frame_idx}:")
        #         for i, anno in enumerate(st.session_state.annotations["frames"][str(frame_idx)]):
        #             st.write(f"  {i+1}. {anno['category']}")
        # else:
        #     st.write("No annotations yet. Click on objects in the video to annotate them.")

if __name__ == "__main__":
    main()
