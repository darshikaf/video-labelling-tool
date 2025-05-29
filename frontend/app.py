import streamlit as st
import os
import sys
import numpy as np
import cv2
from PIL import Image
import tempfile
import streamlit_image_coordinates

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
        st.session_state.selected_class = "Person"  # Default class
    if 'prompt_type' not in st.session_state:
        st.session_state.prompt_type = "point"  # Default prompt type
    if 'points' not in st.session_state:
        st.session_state.points = []  # List of points [(x, y, is_positive), ...]
    if 'boxes' not in st.session_state:
        st.session_state.boxes = []  # List of boxes [(x1, y1, x2, y2), ...]
    if 'awaiting_decision' not in st.session_state:
        st.session_state.awaiting_decision = False  # Flag to show save/cancel buttons
    
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
        
        # Update prompt type based on tool selection
        if tool_type == "Point Prompt":
            st.session_state.prompt_type = "point"
            point_type = st.radio("Point Type", ("Foreground", "Background"))
        elif tool_type == "Box Prompt":
            st.session_state.prompt_type = "box"
        elif tool_type == "Clear Prompts":
            st.session_state.points = []
            st.session_state.boxes = []
            st.session_state.current_mask = None
            st.session_state.awaiting_decision = False
        
        st.header("Settings")
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7)
        
        # Export options
        st.header("Export")
        export_format = st.selectbox(
            "Export Format",
            ["COCO", "YOLO", "CSV", "JSON"]
        )
        
        if export_format == "YOLO":
            yolo_label = st.number_input("YOLO Class ID", 0, 100, 0)
        
        if st.button("Export Annotations"):
            if 'video_path' in locals() and st.session_state.annotations["frames"]:
                export_interface = ExportInterface()
                export_path = export_interface.export_annotations(
                    os.path.basename(video_path),
                    {frame_idx: {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT} for frame_idx in st.session_state.annotations["frames"]},
                    st.session_state.annotations,
                    export_format,
                    "exports"
                )
                st.success(f"Annotations exported to {export_path}")
        
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
            
            # Get current frame index from session state or initialize
            if 'frame_idx' not in st.session_state:
                st.session_state.frame_idx = 0
            
            # Frame navigation controls
            st.write("### Frame Navigation")

            # 1. Navigation buttons in a row
            col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])
            
            with col_nav1:
                if st.button("⏪ -10"):
                    st.session_state.frame_idx = max(0, st.session_state.frame_idx - 10)
                    # Reset annotation workflow state when navigating
                    st.session_state.points = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
            
            with col_nav2:
                if st.button("◀️ Prev"):
                    st.session_state.frame_idx = max(0, st.session_state.frame_idx - 1)
                    # Reset annotation workflow state when navigating
                    st.session_state.points = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
            
            with col_nav3:
                # 2. Direct frame input
                current_frame_number = st.number_input(
                    "Frame #", 
                    min_value=0, 
                    max_value=video_processor.total_frames - 1,
                    value=st.session_state.frame_idx,
                    step=1
                )
                if current_frame_number != st.session_state.frame_idx:
                    st.session_state.frame_idx = current_frame_number
                    # Reset annotation workflow state when navigating
                    st.session_state.points = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
            
            with col_nav4:
                if st.button("Next ▶️"):
                    st.session_state.frame_idx = min(video_processor.total_frames - 1, st.session_state.frame_idx + 1)
                    # Reset annotation workflow state when navigating
                    st.session_state.points = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
            
            with col_nav5:
                if st.button("⏩ +10"):
                    st.session_state.frame_idx = min(video_processor.total_frames - 1, st.session_state.frame_idx + 10)
                    # Reset annotation workflow state when navigating
                    st.session_state.points = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
            
            # 3. Keep the slider for large jumps
            frame_idx = st.slider(
                "Scrub Timeline", 
                0, 
                video_processor.total_frames - 1, 
                st.session_state.frame_idx
            )
            
            # Update session state if slider was moved
            if frame_idx != st.session_state.frame_idx:
                st.session_state.frame_idx = frame_idx
                # Reset annotation workflow state when navigating
                st.session_state.points = []
                st.session_state.current_mask = None
                st.session_state.awaiting_decision = False
            else:
                # Use the value from session state (which might have been updated by buttons)
                frame_idx = st.session_state.frame_idx

            # Get and resize frame
            original_frame = video_processor.get_frame(frame_idx)
            if original_frame is None:
                st.error("Could not read frame from video")
                return
                
            # Resize frame to match canvas dimensions
            current_frame = resize_frame(original_frame, CANVAS_WIDTH, CANVAS_HEIGHT)
            
            # Display instructions based on selected tool and state
            if not st.session_state.awaiting_decision:
                if st.session_state.prompt_type == "point":
                    st.write("👆 **Click on the image to place a point prompt**")
                elif st.session_state.prompt_type == "box":
                    st.write("👆 **Click and drag on the image to create a box prompt**")
            else:
                st.write("✅ **Decide whether to save or cancel this annotation**")
            
            # Only allow new clicks if not awaiting decision on current point
            if not st.session_state.awaiting_decision:
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
                    
                    # Add point to session state (single point only)
                    if st.session_state.prompt_type == "point":
                        is_positive = point_type == "Foreground" if 'point_type' in locals() else True
                        # Replace points array with just this single point
                        st.session_state.points = [(click_x, click_y, is_positive)]
                    
                    # Generate mask from the single point
                    if st.session_state.prompt_type == "point":
                        mask = sam_model.predict(
                            current_frame, 
                            prompt_type="point", 
                            points=st.session_state.points
                        )
                    elif st.session_state.prompt_type == "box" and len(st.session_state.boxes) > 0:
                        mask = sam_model.predict(
                            current_frame, 
                            prompt_type="box", 
                            boxes=st.session_state.boxes
                        )
                    else:
                        mask = None
                    
                    st.session_state.current_mask = mask
                    
                    # Set flag to show save/cancel buttons
                    if mask is not None:
                        st.session_state.awaiting_decision = True
                        st.experimental_rerun()
            
            # If we have a mask to show (and are awaiting decision)
            if st.session_state.current_mask is not None and st.session_state.awaiting_decision:
                # Create visualization
                mask = st.session_state.current_mask
                colored_mask = np.zeros_like(current_frame)
                colored_mask[:,:,1] = mask * 255  # Green channel
                
                # Draw points on the image
                result = current_frame.copy()
                for pt_x, pt_y, is_pos in st.session_state.points:
                    color = (0, 255, 0) if is_pos else (0, 0, 255)
                    cv2.circle(result, (pt_x, pt_y), 5, color, -1)
                
                # Draw boxes if any
                for box in st.session_state.boxes:
                    x1, y1, x2, y2 = box
                    cv2.rectangle(result, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Blend original image with mask
                alpha = 0.7
                result = cv2.addWeighted(result, alpha, colored_mask, 1-alpha, 0)
                
                # Display the result
                st.image(result, caption=f"Frame {frame_idx} with Segmentation")
                
                # Create columns for save/cancel buttons
                col_save, col_cancel = st.columns(2)
                
                with col_save:
                    if st.button("Save This Annotation"):
                        # Store annotation in session state
                        if str(frame_idx) not in st.session_state.annotations["frames"]:
                            st.session_state.annotations["frames"][str(frame_idx)] = []
                        
                        # Add the annotation
                        st.session_state.annotations["frames"][str(frame_idx)].append({
                            "category": st.session_state.selected_class,
                            "mask": mask,
                            "points": st.session_state.points.copy() if st.session_state.prompt_type == "point" else [],
                            "boxes": st.session_state.boxes.copy() if st.session_state.prompt_type == "box" else []
                        })
                        
                        # Get contours from SAM model
                        contours = sam_model.get_contours()
                        
                        # Optional: Export in YOLO format if requested
                        if export_format == "YOLO" and 'yolo_label' in locals():
                            # Create 'annotation' directory at the project root if it doesn't exist
                            annotation_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "annotation")
                            os.makedirs(annotation_dir, exist_ok=True)

                            # Save the image in the annotation directory
                            temp_img_path = os.path.join(annotation_dir, f"frame_{frame_idx}.jpg")
                            cv2.imwrite(temp_img_path, cv2.cvtColor(original_frame, cv2.COLOR_RGB2BGR))
                            
                            # Use the model's built-in YOLO export
                            sam_results = [type('obj', (), {'masks': type('masks', (), {'data': [mask]})()})]
                            sam_model.save_yolo_labels(
                                temp_img_path, 
                                original_frame, 
                                frame_idx, 
                                sam_results, 
                                yolo_label
                            )
                        
                        # Clear points, mask, and reset workflow state
                        st.session_state.points = []
                        st.session_state.current_mask = None
                        st.session_state.awaiting_decision = False
                        st.experimental_rerun()
                
                with col_cancel:
                    if st.button("Cancel Annotation"):
                        # Clear points, mask, and reset workflow state
                        st.session_state.points = []
                        st.session_state.current_mask = None
                        st.session_state.awaiting_decision = False
                        st.experimental_rerun()
            
            # Display the base image if not showing the mask
            elif not st.session_state.awaiting_decision:
                st.image(current_frame, caption=f"Frame {frame_idx}")
            
        # Annotations section
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
                    
                    # Option to delete individual annotations
                    if st.button(f"Delete annotation {i+1}", key=f"delete_{frame_idx}_{i}"):
                        st.session_state.annotations["frames"][str(frame_idx)].pop(i)
                        if not st.session_state.annotations["frames"][str(frame_idx)]:
                            del st.session_state.annotations["frames"][str(frame_idx)]
                        st.experimental_rerun()
        else:
            st.write("No annotations yet. Click on objects in the video to annotate them.")

if __name__ == "__main__":
    main()
