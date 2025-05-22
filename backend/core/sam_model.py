import numpy as np
import cv2
import os
from ultralytics import SAM
from typing import Tuple, List, Optional, Dict
from pathlib import Path

class SAMModel:
    """
    Implementation of Segment Anything Model (SAM) integration using Ultralytics
    """
    def __init__(self, model_type="vit_b"):
        """
        Initialize the SAM model
        
        Args:
            model_type (str): Model type identifier
        """
        self.model_type = model_type
        # Load the SAM model
        model_path = Path(__file__).parent.parent.parent / "models" / "sam2.1_b.pt"
        model_dir = model_path.parent
        
        # Create models directory if it doesn't exist
        model_dir.mkdir(exist_ok=True, parents=True)
        
        if not model_path.exists():
            try:
                print(f"Model file not found. Attempting to download...")
                import torch
                
                # Download model from Ultralytics
                torch.hub.download_url_to_file(
                    "https://github.com/ultralytics/assets/releases/download/v8.2.0/sam2.1_b.pt",
                    str(model_path)
                )
                print(f"Model downloaded successfully to {model_path}")
            except Exception as e:
                print(f"Failed to download model: {e}")
                print(f"Using simulation mode.")
                self.model = None
                return
                
        try:
            self.model = SAM(model_path)
            print(f"SAM model loaded successfully from {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            print(f"Falling back to simulation mode.")
            self.model = None
            
        # Track interaction state
        self.points = []
        self.labels = []
        self.contours = None
        
    def _add_point(self, x: int, y: int, label: int=1):
        """
        Add a new point with its label
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            label (int): 1 for foreground, 0 for background
        """
        self.points.append((x, y))
        self.labels.append(label)
        
    def _run_segmentation(self, image: np.ndarray) -> Optional[List[Dict]]:
        """
        Run the SAM model with the current points
        
        Args:
            image (numpy.ndarray): Input image
            
        Returns:
            Optional[List[Dict]]: Segmentation results
        """
        if self.model is None:
            return None
            
        if len(self.points) != len(self.labels):
            return None
        
        try:
            results = self.model.predict(
                source=image, 
                points=self.points, 
                labels=self.labels, 
                show=False
            )

            if results and hasattr(results[0], 'masks') and results[0].masks is not None:
                for mask in results[0].masks.data:
                    mask_np = mask.cpu().numpy().astype("uint8") * 255
                    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    self.contours = contours
                    
            return results
        except Exception as e:
            print(f"Segmentation error: {e}")
            return None
            
    def predict(self, image, prompt_type="point", points=None, boxes=None, masks=None):
        """
        Run SAM prediction based on prompts
        
        Args:
            image: Input image
            prompt_type: Type of prompt (point, box, mask)
            points: List of point prompts [(x, y, is_positive), ...]
            boxes: List of box prompts [(x1, y1, x2, y2), ...]
            masks: List of mask prompts
            
        Returns:
            numpy.ndarray: Binary mask
        """
        h, w = image.shape[:2]
        result_mask = np.zeros((h, w), dtype=np.uint8)
        
        # Reset points and labels
        # self.points = []
        # self.labels = []
        
        for point in points:
            self._add_point(point[0], point[1])

        if self.model is None:
            # Fallback to simulation mode if model isn't loaded
            if prompt_type == "point" and points:
                # Create a circular mask centered on each point
                for x, y, is_positive in points:
                    if is_positive:
                        radius = min(h, w) // 8
                        cv2.circle(result_mask, (int(x), int(y)), radius, 1, -1)
            elif prompt_type == "box" and boxes:
                # Create a mask inside each box
                for x1, y1, x2, y2 in boxes:
                    cv2.rectangle(result_mask, (int(x1), int(y1)), (int(x2), int(y2)), 1, -1)
            else:
                # Random blob as placeholder
                for _ in range(3):
                    cx = np.random.randint(w//4, 3*w//4)
                    cy = np.random.randint(h//4, 3*h//4)
                    radius = np.random.randint(min(h, w) // 8, min(h, w) // 3)
                    cv2.circle(result_mask, (cx, cy), radius, 1, -1)
                
            return result_mask
        
        # Use the actual model
        if prompt_type == "point" and points:
            sam_points = []
            sam_labels = []
            
            for x, y, is_positive in points:
                sam_points.append((int(x), int(y)))
                sam_labels.append(1 if is_positive else 0)
                
            results = self._run_segmentation(image)
            
            if results and hasattr(results[0], 'masks') and results[0].masks is not None:
                for i, mask in enumerate(results[0].masks.data):
                    mask_np = mask.cpu().numpy().astype("uint8")
                    result_mask = np.logical_or(result_mask, mask_np).astype(np.uint8)
        
        return result_mask
        
    def get_contours(self):
        """
        Get the contours of the segmented image
        
        Returns:
            list: Detected contours
        """
        return self.contours
        
    def save_yolo_labels(self, image_path: str, image_frame: np.ndarray, video_frame_number: int, sam_results, label: int):
        """
        Save segmentation results in YOLOv11 format
        
        Args:
            image_path (str): Path to the original image
            image_frame (numpy.ndarray): Image frame
            video_frame_number (int): Frame number in video
            sam_results: SAM segmentation results
            label (int): Class label
        """
        image_name = os.path.basename(image_path).split('.')[0]
        label_path = os.path.join(os.path.dirname(image_path), image_name + str(video_frame_number) + ".txt")
        frame_path = os.path.join(os.path.dirname(image_path), image_name + str(video_frame_number) + ".jpg")

        with open(label_path, 'w') as label_file:
            height, width, _ = image_frame.shape
            if sam_results and hasattr(sam_results[0], 'masks') and sam_results[0].masks is not None:
                for mask in sam_results[0].masks.data:
                    # mask_np = mask.cpu().numpy().astype("uint8") * 255
                    if hasattr(mask, "cpu"):
                        mask_np = mask.cpu().numpy().astype("uint8") * 255
                    else:
                        mask_np = mask.astype("uint8") * 255
                    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Normalize points to be between 0 and 1
                    normalized_points = []
                    for contour in contours:
                        for point in contour:
                            norm_x = point[0][0] / width
                            norm_y = point[0][1] / height
                            normalized_points.append(f"{norm_x} {norm_y}")

                    if len(normalized_points) > 2:
                        label_file.write(f"{label} " + " ".join(normalized_points) + "\n")
                        cv2.imwrite(frame_path, cv2.cvtColor(image_frame, cv2.COLOR_RGB2BGR))
        
        print(f"Labels saved in YOLO format at {label_path}")
