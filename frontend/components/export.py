# frontend/components/export.py
import streamlit as st
import json
import os
import numpy as np
import cv2
from PIL import Image
import datetime
import shutil

class ExportInterface:
    """
    Component for handling annotation exports in various formats
    """
    def __init__(self):
        """Initialize the export interface"""
        self.supported_formats = ["COCO", "YOLO", "CSV", "JSON"]
    
    def export_annotations(self, video_name, frames, annotations, export_format="COCO", export_dir="exports"):
        """
        Export annotations in the specified format
        
        Args:
            video_name (str): Name of the video file
            frames (dict): Dictionary mapping frame indices to frame data
            annotations (dict): Dictionary containing annotation data
            export_format (str): Format to export ("COCO", "YOLO", etc.)
            export_dir (str): Directory to save exports
            
        Returns:
            str: Path to exported file or directory
        """
        # Create exports directory if it doesn't exist
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{os.path.splitext(video_name)[0]}_{timestamp}"
        
        if export_format == "COCO":
            return self._export_coco(base_filename, frames, annotations, export_dir)
        elif export_format == "YOLO":
            return self._export_yolo(base_filename, frames, annotations, export_dir)
        elif export_format == "CSV":
            return self._export_csv(base_filename, frames, annotations, export_dir)
        elif export_format == "JSON":
            return self._export_json(base_filename, frames, annotations, export_dir)
        else:
            return None
    
    def _export_coco(self, base_filename, frames, annotations, export_dir):
        """Export in COCO format"""
        output_file = os.path.join(export_dir, f"{base_filename}_coco.json")
        
        # Create COCO format structure
        coco_data = {
            "info": {
                "description": "SAM Video Segmentation Annotations",
                "date_created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "images": [],
            "annotations": [],
            "categories": []
        }
        
        # Add categories
        category_mapping = {}
        for i, category in enumerate(annotations.get("categories", [])):
            category_id = i + 1
            category_mapping[category] = category_id
            coco_data["categories"].append({
                "id": category_id,
                "name": category,
                "supercategory": "object"
            })
        
        # Add images and annotations
        annotation_id = 1
        for frame_idx, frame_data in frames.items():
            # Add image info
            image_id = int(frame_idx) + 1
            coco_data["images"].append({
                "id": image_id,
                "file_name": f"frame_{frame_idx:06d}.jpg",
                "width": frame_data.get("width", 0),
                "height": frame_data.get("height", 0)
            })
            
            # Add annotations for this frame
            frame_annotations = annotations.get("frames", {}).get(str(frame_idx), [])
            for anno in frame_annotations:
                mask = anno.get("mask")
                if mask is not None:
                    # Convert mask to RLE or polygon
                    # (Simplified for MVP - in practice would use pycocotools)
                    contours, _ = cv2.findContours(
                        (mask > 0).astype(np.uint8), 
                        cv2.RETR_EXTERNAL, 
                        cv2.CHAIN_APPROX_SIMPLE
                    )
                    
                    segmentation = []
                    for contour in contours:
                        contour = contour.flatten().tolist()
                        if len(contour) > 4:  # Valid polygons have at least 3 points
                            segmentation.append(contour)
                    
                    if segmentation:
                        # Calculate bounding box
                        x, y, w, h = cv2.boundingRect((mask > 0).astype(np.uint8))
                        
                        coco_data["annotations"].append({
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": category_mapping.get(anno.get("category"), 1),
                            "segmentation": segmentation,
                            "area": float(np.sum(mask)),
                            "bbox": [x, y, w, h],
                            "iscrowd": 0
                        })
                        annotation_id += 1
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(coco_data, f, indent=2)
        
        return output_file
    
    def _export_yolo(self, base_filename, frames, annotations, export_dir):
        """Export in YOLO format"""
        # Create directory for YOLO format (images + labels)
        yolo_dir = os.path.join(export_dir, f"{base_filename}_yolo")
        os.makedirs(os.path.join(yolo_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(yolo_dir, "labels"), exist_ok=True)
        
        # Create classes.txt
        classes_file = os.path.join(yolo_dir, "classes.txt")
        with open(classes_file, 'w') as f:
            for category in annotations.get("categories", []):
                f.write(f"{category}\n")
        
        # For each frame with annotations, create a label file
        for frame_idx, frame_data in frames.items():
            frame_annotations = annotations.get("frames", {}).get(str(frame_idx), [])
            
            if frame_annotations:
                # Create label file
                label_file = os.path.join(yolo_dir, "labels", f"frame_{int(frame_idx):06d}.txt")
                
                with open(label_file, 'w') as f:
                    for anno in frame_annotations:
                        # Get class index
                        class_idx = annotations.get("categories", []).index(anno.get("category", ""))
                        
                        # Handle segmentation masks - use SAM model's format
                        mask = anno.get("mask")
                        if mask is not None:
                            # For segmentation:
                            contours, _ = cv2.findContours(
                                (mask > 0).astype(np.uint8), 
                                cv2.RETR_EXTERNAL, 
                                cv2.CHAIN_APPROX_SIMPLE
                            )
                            
                            # Format for YOLO segmentation annotation (polygon format)
                            for contour in contours:
                                img_w = frame_data.get("width", 1)
                                img_h = frame_data.get("height", 1)
                                
                                # Normalize points
                                points = []
                                for pt in contour:
                                    x, y = pt[0]
                                    norm_x = x / img_w
                                    norm_y = y / img_h
                                    points.extend([norm_x, norm_y])
                                
                                if len(points) > 5:  # At least 3 points (6 values)
                                    points_str = " ".join([f"{p:.6f}" for p in points])
                                    f.write(f"{class_idx} {points_str}\n")
                            
                            # Calculate bounding box (for regular YOLO detection)
                            x, y, w, h = cv2.boundingRect((mask > 0).astype(np.uint8))
                            
                            # Convert to YOLO format (normalized center x, center y, width, height)
                            img_w = frame_data.get("width", 1)
                            img_h = frame_data.get("height", 1)
                            
                            center_x = (x + w/2) / img_w
                            center_y = (y + h/2) / img_h
                            norm_w = w / img_w
                            norm_h = h / img_h
                
        return yolo_dir
    
    def _export_csv(self, base_filename, frames, annotations, export_dir):
        """Export in CSV format"""
        output_file = os.path.join(export_dir, f"{base_filename}_annotations.csv")
        
        with open(output_file, 'w') as f:
            # Write header
            f.write("frame,category,x,y,width,height,area\n")
            
            # Write data
            for frame_idx, frame_data in frames.items():
                frame_annotations = annotations.get("frames", {}).get(str(frame_idx), [])
                
                for anno in frame_annotations:
                    category = anno.get("category", "")
                    mask = anno.get("mask")
                    
                    if mask is not None:
                        # Calculate bounding box
                        x, y, w, h = cv2.boundingRect((mask > 0).astype(np.uint8))
                        area = int(np.sum(mask))
                        
                        # Write to CSV
                        f.write(f"{frame_idx},{category},{x},{y},{w},{h},{area}\n")
        
        return output_file
    
    def _export_json(self, base_filename, frames, annotations, export_dir):
        """Export in simple JSON format"""
        output_file = os.path.join(export_dir, f"{base_filename}_annotations.json")
        
        # Create simplified JSON structure
        json_data = {
            "metadata": {
                "video_name": base_filename,
                "date_created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "categories": annotations.get("categories", [])
            },
            "frames": {}
        }
        
        # Add frame data
        for frame_idx, frame_data in frames.items():
            frame_annotations = annotations.get("frames", {}).get(str(frame_idx), [])
            
            if frame_annotations:
                json_data["frames"][frame_idx] = []
                
                for anno in frame_annotations:
                    category = anno.get("category", "")
                    mask = anno.get("mask")
                    
                    if mask is not None:
                        # Calculate bounding box
                        x, y, w, h = cv2.boundingRect((mask > 0).astype(np.uint8))
                        
                        # For JSON export, encode contours
                        contours, _ = cv2.findContours(
                            (mask > 0).astype(np.uint8), 
                            cv2.RETR_EXTERNAL, 
                            cv2.CHAIN_APPROX_SIMPLE
                        )
                        
                        contour_points = []
                        for contour in contours:
                            contour_points.append(contour.flatten().tolist())
                        
                        json_data["frames"][frame_idx].append({
                            "category": category,
                            "bbox": [int(x), int(y), int(w), int(h)],
                            "contours": contour_points,
                            "area": int(np.sum(mask))
                        })
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        return output_file
    
    def render_export_ui(self):
        """
        Render the export UI elements
        
        Returns:
            dict: Dictionary containing export configuration
        """
        st.subheader("Export Annotations")
        
        # Select export format
        export_format = st.selectbox(
            "Export Format",
            self.supported_formats,
            index=0
        )
        
        # Additional export options based on format
        export_options = {}
        
        if export_format == "COCO":
            export_options["include_images"] = st.checkbox("Include Frame Images", value=True)
        
        elif export_format == "YOLO":
            export_options["export_masks"] = st.checkbox("Export Segmentation Masks", value=True)
            st.info("YOLO format supports both bounding boxes and polygon segmentation.")
        
        # Export button and directory
        export_dir = st.text_input("Export Directory", value="exports")
        
        return {
            "format": export_format,
            "options": export_options,
            "directory": export_dir
        }
