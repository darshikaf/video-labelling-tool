import streamlit as st
import os
import sys
import numpy as np
import cv2
import datetime
import json
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
from frontend.components.polygon_editor import PolygonEditor  # Import our new component

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
        return np.zeros((target_height, target_width, 3), dtype=np.uint8)
        
    h, w = frame.shape[:2]
    
    # Calculate target dimensions while maintaining aspect ratio
    if w/h > target_width/target_height:
        new_w = target_width
        new_h = int(h * (target_width / w))
    else:
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
    if 'editing_mode' not in st.session_state:
        st.session_state.editing_mode = "default"  # Can be "default" or "polygon"
    if 'polygon_points' not in st.session_state:
        st.session_state.polygon_points = []  # For polygon editing
    if 'polygon_editor' not in st.session_state:
        st.session_state.polygon_editor = PolygonEditor()  # Initialize polygon editor

    # App header
    st.title("SAM Video Segmentation Tool")
    
    # Sidebar - Video upload and settings
    with st.sidebar:
        st.header("Settings")
        
        # Video upload
        uploaded_file = st.file_uploader("Upload Video", type=["mp4", "avi", "mov", "mkv"])
        
        # Class selection
        st.subheader("Classes")
        default_classes = ["Person", "Vehicle", "Animal", "Object"]
        
        # Use existing categories or default ones
        if not st.session_state.annotations["categories"]:
            st.session_state.annotations["categories"] = default_classes
        
        selected_class = st.selectbox(
            "Select Class", 
            st.session_state.annotations["categories"],
            index=default_classes.index(st.session_state.selected_class) if st.session_state.selected_class in default_classes else 0
        )
        st.session_state.selected_class = selected_class
        
        # Add new class option
        new_class = st.text_input("Add New Class")
        if st.button("Add Class") and new_class and new_class not in st.session_state.annotations["categories"]:
            st.session_state.annotations["categories"].append(new_class)
            st.success(f"Added class: {new_class}")
        
        # Prompt type selection
        st.subheader("Prompt Type")
        prompt_options = ["point", "box"]
        prompt_type = st.radio("Select Prompt Type", prompt_options, index=prompt_options.index(st.session_state.prompt_type))
        st.session_state.prompt_type = prompt_type
        
        # Point mode selection (positive/negative)
        if prompt_type == "point":
            st.subheader("Point Mode")
            point_mode = st.radio("Select Point Mode", ["Positive (Include)", "Negative (Exclude)"])
            st.session_state.point_mode = point_mode == "Positive (Include)"
        
    # Main content area
    if uploaded_file is None:
        st.info("Please upload a video file to begin")
    else:
        # Save uploaded file to temp file
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        video_path = tfile.name
        
        # Initialize video player and SAM model
        video_processor = VideoProcessor(video_path)
        sam_model = SAMModel()
        
        # Timeline controls
        st.subheader("Timeline")
        
        col_timeline1, col_timeline2 = st.columns([3, 1])
        
        with col_timeline1:
            frame_idx = st.slider(
                "Frame", 
                min_value=0, 
                max_value=video_processor.total_frames-1, 
                value=0
            )
            
        with col_timeline2:
            frame_time = frame_idx / video_processor.fps
            minutes = int(frame_time // 60)
            seconds = frame_time % 60
            st.text(f"Time: {minutes:02d}:{seconds:05.2f}")
        
        # Get current frame
        current_frame = video_processor.get_frame(frame_idx)
        current_frame_resized = resize_frame(current_frame)
        
        # Display annotations for the current frame
        existing_annotations = []
        if str(frame_idx) in st.session_state.annotations["frames"]:
            existing_annotations = st.session_state.annotations["frames"][str(frame_idx)]
        
        if existing_annotations:
            st.subheader(f"Existing Annotations: {len(existing_annotations)}")
            
            # Visualize existing annotations
            anno_result = current_frame_resized.copy()
            
            # Apply all annotations as overlays
            for i, anno in enumerate(existing_annotations):
                # Create colored overlay for this annotation
                overlay = np.zeros_like(anno_result)
                
                # Get random color for this class (but consistent for the same class name)
                class_name = anno["category"]
                class_idx = st.session_state.annotations["categories"].index(class_name) if class_name in st.session_state.annotations["categories"] else 0
                
                # Generate color from class index
                r = (class_idx * 100 + 50) % 255
                g = (class_idx * 50 + 100) % 255
                b = (class_idx * 80 + 20) % 255
                color = (r, g, b)
                
                # Apply mask with this color
                mask = anno["mask"]
                overlay[:,:,0] = mask * color[0]
                overlay[:,:,1] = mask * color[1]
                overlay[:,:,2] = mask * color[2]
                
                # Blend with result
                alpha = 0.5
                cv2.addWeighted(anno_result, 1, overlay, alpha, 0, anno_result)
                
                # Draw annotation label
                # Find the top-left corner of the mask
                y_indices, x_indices = np.where(mask > 0)
                if len(y_indices) > 0 and len(x_indices) > 0:
                    x_min = np.min(x_indices)
                    y_min = np.min(y_indices)
                    
                    # Draw label background
                    label_text = f"{i+1}: {class_name}"
                    (text_width, text_height), _ = cv2.getTextSize(
                        label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
                    )
                    cv2.rectangle(
                        anno_result,
                        (x_min, y_min - 20),
                        (x_min + text_width, y_min),
                        color,
                        -1
                    )
                    
                    # Draw text
                    cv2.putText(
                        anno_result,
                        label_text,
                        (x_min, y_min - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        1
                    )
            
            # Show the result with all annotations
            st.image(anno_result, caption=f"Frame {frame_idx} with Annotations")
            
            # Let user delete annotations
            if st.button("Delete Last Annotation"):
                if str(frame_idx) in st.session_state.annotations["frames"] and st.session_state.annotations["frames"][str(frame_idx)]:
                    st.session_state.annotations["frames"][str(frame_idx)].pop()
                    st.experimental_rerun()
        
        # Create new annotation section
        st.subheader("Create New Annotation")
        
        # Display the current frame for annotation
        if st.session_state.awaiting_decision:
            # If we already have a mask, don't create a new one until decision
            pass
        else:
            # Show the image for prompting
            result = current_frame_resized.copy()
            
            # Draw existing points
            for pt_x, pt_y, is_pos in st.session_state.points:
                color = (0, 255, 0) if is_pos else (0, 0, 255)
                cv2.circle(result, (pt_x, pt_y), 5, color, -1)
                
            # Draw existing boxes
            for box in st.session_state.boxes:
                x1, y1, x2, y2 = box
                cv2.rectangle(result, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
            # Display the image and get click coordinates
            st.image(result, caption=f"Frame {frame_idx}")
            
            # Get click coordinates based on prompt type
            if st.session_state.prompt_type == "point":
                coordinates = streamlit_image_coordinates.streamlit_image_coordinates(
                    result,
                    key=f"frame_coords_{frame_idx}"
                )
                
                if coordinates:
                    x, y = coordinates['x'], coordinates['y']
                    is_positive = st.session_state.point_mode
                    
                    # Add the point to state
                    st.session_state.points.append((x, y, is_positive))
                    
                    # Get prediction from SAM
                    mask = sam_model.predict(
                        current_frame_resized, 
                        prompt_type="point", 
                        points=st.session_state.points
                    )
                    
                    st.session_state.current_mask = mask
                    st.session_state.awaiting_decision = True
                    st.experimental_rerun()
                    
            elif st.session_state.prompt_type == "box":
                # For box prompts, need two clicks
                if len(st.session_state.boxes) == 0:
                    # First click sets the top-left corner
                    coordinates = streamlit_image_coordinates.streamlit_image_coordinates(
                        result,
                        key=f"box_start_{frame_idx}"
                    )
                    
                    if coordinates:
                        x1, y1 = coordinates['x'], coordinates['y']
                        st.session_state.boxes.append((x1, y1, x1, y1))  # Placeholder for full box
                        st.session_state.temp_box_started = True
                        st.experimental_rerun()
                        
                elif len(st.session_state.boxes) == 1 and hasattr(st.session_state, 'temp_box_started'):
                    # Second click sets the bottom-right corner
                    coordinates = streamlit_image_coordinates.streamlit_image_coordinates(
                        result,
                        key=f"box_end_{frame_idx}"
                    )
                    
                    if coordinates:
                        x2, y2 = coordinates['x'], coordinates['y']
                        x1, y1, _, _ = st.session_state.boxes[0]
                        
                        # Update the box
                        st.session_state.boxes[0] = (x1, y1, x2, y2)
                        
                        # Get prediction from SAM
                        mask = sam_model.predict(
                            current_frame_resized, 
                            prompt_type="box", 
                            boxes=st.session_state.boxes
                        )
                        
                        st.session_state.current_mask = mask
                        st.session_state.awaiting_decision = True
                        delattr(st.session_state, 'temp_box_started')
                        st.experimental_rerun()
                        
            # Reset button
            if st.session_state.points or st.session_state.boxes:
                if st.button("Reset Points/Boxes"):
                    st.session_state.points = []
                    st.session_state.boxes = []
                    if hasattr(st.session_state, 'temp_box_started'):
                        delattr(st.session_state, 'temp_box_started')
                    st.experimental_rerun()
        
        # Display and process mask if we have one
        if st.session_state.current_mask is not None and st.session_state.awaiting_decision:
            # Create visualization
            mask = st.session_state.current_mask
            colored_mask = np.zeros_like(current_frame_resized)
            colored_mask[:,:,1] = mask * 255  # Green channel
            
            # Draw points on the image
            result = current_frame_resized.copy()
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
            
            # Add Mask Adjustment Controls
            st.write("### Adjust Mask")
            
            edit_mode = st.radio(
                "Edit Mode",
                ["Basic Adjustments", "Polygon Editing"],
                key="edit_mode_selection"
            )
            
            if edit_mode == "Basic Adjustments":
                col_adjustment1, col_adjustment2 = st.columns(2)
                
                with col_adjustment1:
                    adjustment_type = st.selectbox(
                        "Adjustment Type",
                        ["Expand", "Contract", "Smooth"],
                        key="mask_adjustment_type"
                    )
                
                with col_adjustment2:
                    adjustment_amount = st.slider(
                        "Adjustment Amount", 
                        min_value=1, 
                        max_value=20, 
                        value=5,
                        key="mask_adjustment_amount"
                    )
                
                if st.button("Apply Adjustment"):
                    # Apply basic morphological operations
                    mask_uint8 = mask.astype(np.uint8)
                    kernel = np.ones((adjustment_amount, adjustment_amount), np.uint8)
                    
                    if adjustment_type == "Expand":
                        adjusted = cv2.dilate(mask_uint8, kernel, iterations=1)
                    elif adjustment_type == "Contract":
                        adjusted = cv2.erode(mask_uint8, kernel, iterations=1)
                    elif adjustment_type == "Smooth":
                        adjusted = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel)
                        adjusted = cv2.morphologyEx(adjusted, cv2.MORPH_CLOSE, kernel)
                    
                    st.session_state.current_mask = adjusted
                    st.experimental_rerun()
                    
            elif edit_mode == "Polygon Editing":
                # Initialize polygon editor with current mask if not already in polygon mode
                if st.session_state.editing_mode != "polygon":
                    # Convert mask to polygon
                    polygon_points = st.session_state.polygon_editor.mask_to_polygon(mask)
                    st.session_state.polygon_editor.polygon_points = polygon_points
                    st.session_state.editing_mode = "polygon"
                
                # Show polygon editing tools
                polygon_tool = st.radio(
                    "Polygon Tool",
                    ["Add Nodes", "Move Nodes", "Delete Nodes"],
                    key="polygon_tool"
                )
                
                # Render the polygon on the image
                polygon_result = st.session_state.polygon_editor.render_polygon(current_frame_resized)
                
                # Display the image with polygon for editing
                st.image(polygon_result, caption="Polygon Editing Mode")
                
                # Handle polygon interactions
                coordinates = streamlit_image_coordinates.streamlit_image_coordinates(
                    polygon_result,
                    key=f"polygon_edit_{frame_idx}"
                )
                
                if coordinates:
                    x, y = coordinates['x'], coordinates['y']
                    
                    # Handle different polygon tools
                    if polygon_tool == "Add Nodes":
                        # Find nearest edge and add node
                        nearest = st.session_state.polygon_editor.find_nearest_edge(x, y)
                        if nearest:
                            edge_idx, t_pos = nearest
                            st.session_state.polygon_editor.add_node_at_edge(edge_idx, t_pos)
                            st.experimental_rerun()
                    
                    elif polygon_tool == "Move Nodes":
                        # Find nearest node
                        node_idx = st.session_state.polygon_editor.find_nearest_node(x, y)
                        if node_idx is not None:
                            # Move the node
                            st.session_state.polygon_editor.move_node(node_idx, x, y)
                            st.experimental_rerun()
                    
                    elif polygon_tool == "Delete Nodes":
                        # Find and delete nearest node
                        node_idx = st.session_state.polygon_editor.find_nearest_node(x, y)
                        if node_idx is not None:
                            success = st.session_state.polygon_editor.delete_node(node_idx)
                            if success:
                                st.experimental_rerun()
                            else:
                                st.warning("Cannot delete node: minimum 3 nodes required")
                
                # Apply polygon edits to the mask
                if st.button("Apply Polygon Edits"):
                    # Convert polygon back to mask
                    mask_shape = mask.shape
                    new_mask = st.session_state.polygon_editor.polygon_to_mask(
                        st.session_state.polygon_editor.polygon_points,
                        mask_shape
                    )
                    
                    # Update the current mask
                    st.session_state.current_mask = new_mask
                    st.session_state.editing_mode = "default"  # Exit polygon editing mode
                    st.experimental_rerun()
                
                if st.button("Cancel Polygon Edits"):
                    st.session_state.editing_mode = "default"
                    st.experimental_rerun()
            
            # Display the current image with mask (when not in polygon edit mode)
            if st.session_state.editing_mode != "polygon":
                st.image(result, caption=f"Frame {frame_idx} with Segmentation")
            
            # Save/Cancel buttons
            col_save, col_cancel = st.columns(2)
            
            with col_save:
                if st.button("Save This Annotation"):
                    # Store annotation in session state
                    if str(frame_idx) not in st.session_state.annotations["frames"]:
                        st.session_state.annotations["frames"][str(frame_idx)] = []
                    
                    # Add the annotation
                    st.session_state.annotations["frames"][str(frame_idx)].append({
                        "category": st.session_state.selected_class,
                        "mask": st.session_state.current_mask,
                        "points": st.session_state.points.copy() if st.session_state.prompt_type == "point" else [],
                        "boxes": st.session_state.boxes.copy() if st.session_state.prompt_type == "box" else []
                    })
                    
                    # Reset state
                    st.session_state.points = []
                    st.session_state.boxes = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
                    st.session_state.editing_mode = "default"
                    st.experimental_rerun()
            
            with col_cancel:
                if st.button("Cancel Annotation"):
                    # Clear state
                    st.session_state.points = []
                    st.session_state.boxes = []
                    st.session_state.current_mask = None
                    st.session_state.awaiting_decision = False
                    st.session_state.editing_mode = "default"
                    st.experimental_rerun()
        
        # Export section
        st.subheader("Export Annotations")
        
        export_format = st.selectbox(
            "Export Format",
            ["COCO JSON", "YOLO", "Custom JSON"]
        )
        
        if st.button("Export Annotations"):
            # Create export directory
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            
            # Generate timestamp for unique filenames
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if export_format == "COCO JSON":
                # Export in COCO format
                coco_data = {
                    "info": {
                        "description": "SAM Video Segmentation Annotations",
                        "date_created": timestamp
                    },
                    "images": [],
                    "annotations": [],
                    "categories": []
                }
                
                # Add categories
                for i, category in enumerate(st.session_state.annotations["categories"]):
                    coco_data["categories"].append({
                        "id": i+1,
                        "name": category,
                        "supercategory": "object"
                    })
                
                # Add frames and annotations
                annotation_id = 1
                for frame_idx_str, frame_annotations in st.session_state.annotations["frames"].items():
                    frame_idx = int(frame_idx_str)
                    
                    # Add image info
                    coco_data["images"].append({
                        "id": frame_idx,
                        "file_name": f"frame_{frame_idx:06d}.jpg",
                        "width": CANVAS_WIDTH,
                        "height": CANVAS_HEIGHT
                    })
                    
                    # Add annotations for this frame
                    for anno in frame_annotations:
                        category_name = anno["category"]
                        category_id = st.session_state.annotations["categories"].index(category_name) + 1
                        
                        # Convert binary mask to RLE or polygons
                        mask = anno["mask"]
                        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        # Skip if no contours found
                        if not contours:
                            continue
                            
                        segmentations = []
                        for contour in contours:
                            # Flatten contour to [x1,y1,x2,y2,...] format
                            contour = contour.flatten().tolist()
                            if len(contour) > 4:  # Need at least 2 points
                                segmentations.append(contour)
                        
                        # Get bounding box
                        y_indices, x_indices = np.where(mask > 0)
                        if len(y_indices) == 0 or len(x_indices) == 0:
                            continue
                            
                        x_min, y_min = np.min(x_indices), np.min(y_indices)
                        x_max, y_max = np.max(x_indices), np.max(y_indices)
                        width = x_max - x_min
                        height = y_max - y_min
                        
                        coco_data["annotations"].append({
                            "id": annotation_id,
                            "image_id": frame_idx,
                            "category_id": category_id,
                            "segmentation": segmentations,
                            "area": float(np.sum(mask)),
                            "bbox": [float(x_min), float(y_min), float(width), float(height)],
                            "iscrowd": 0
                        })
                        
                        annotation_id += 1
                
                # Save COCO JSON
                filename = os.path.join(export_dir, f"annotations_{timestamp}.json")
                with open(filename, 'w') as f:
                    json.dump(coco_data, f)
                
                st.success(f"Exported annotations to {filename}")
                
            elif export_format == "YOLO":
                # Create subdirectories for YOLO format
                labels_dir = os.path.join(export_dir, "labels")
                os.makedirs(labels_dir, exist_ok=True)
                
                # Create class mapping
                classes = st.session_state.annotations["categories"]
                class_mapping = {name: i for i, name in enumerate(classes)}
                
                # Save class names
                with open(os.path.join(export_dir, "classes.txt"), 'w') as f:
                    for cls_name in classes:
                        f.write(f"{cls_name}\n")
                
                # Export annotations for each frame
                for frame_idx_str, frame_annotations in st.session_state.annotations["frames"].items():
                    frame_idx = int(frame_idx_str)
                    
                    # Create label file for this frame
                    label_filename = os.path.join(labels_dir, f"frame_{frame_idx:06d}.txt")
                    
                    with open(label_filename, 'w') as f:
                        # For each annotation in this frame
                        for anno in frame_annotations:
                            category_name = anno["category"]
                            class_id = class_mapping.get(category_name, 0)
                            
                            mask = anno["mask"]
                            # Skip if mask is empty
                            if np.sum(mask) == 0:
                                continue
                                
                            # Get polygon points for this mask
                            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Write each contour as a separate object
                            for contour in contours:
                                # Scale points to 0-1 range
                                polygon_points = []
                                for point in contour.reshape(-1, 2):
                                    x, y = point
                                    x_norm = x / CANVAS_WIDTH
                                    y_norm = y / CANVAS_HEIGHT
                                    polygon_points.extend([x_norm, y_norm])
                                
                                # Format: class_id x1 y1 x2 y2 ... xn yn
                                line = f"{class_id} " + " ".join(f"{p:.6f}" for p in polygon_points)
                                f.write(line + "\n")
                
                st.success(f"Exported annotations in YOLO format to {export_dir}")
                
            elif export_format == "Custom JSON":
                # Export as custom JSON format
                filename = os.path.join(export_dir, f"annotations_{timestamp}_custom.json")
                
                # Prepare export data
                export_data = {
                    "info": {
                        "description": "SAM Video Segmentation Custom Annotations",
                        "date_created": timestamp,
                        "categories": st.session_state.annotations["categories"]
                    },
                    "frames": {}
                }
                
                # Process each frame
                for frame_idx_str, frame_annotations in st.session_state.annotations["frames"].items():
                    export_data["frames"][frame_idx_str] = []
                    
                    # Process each annotation
                    for anno in frame_annotations:
                        mask = anno["mask"]
                        
                        # Convert mask to more efficient representation
                        mask_rle = mask.astype(np.uint8).tobytes()
                        
                        # Store annotation data
                        export_data["frames"][frame_idx_str].append({
                            "category": anno["category"],
                            "mask_shape": list(mask.shape),
                            "points": anno["points"],
                            "boxes": anno["boxes"]
                        })
                
                # Save as JSON
                with open(filename, 'w') as f:
                    json.dump(export_data, f)
                
                st.success(f"Exported annotations to {filename}")

if __name__ == "__main__":
    main()
