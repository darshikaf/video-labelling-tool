import numpy as np
import cv2
import os
from ultralytics import SAM
from typing import Tuple, List, Optional, Dict
from pathlib import Path
import logging
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

class SAMModel:
    """
    Implementation of Segment Anything Model (SAM) integration using Ultralytics
    Exact copy of working Streamlit implementation
    """
    def __init__(self, model_type="vit_b"):
        """
        Initialize the SAM model
        
        Args:
            model_type (str): Model type identifier
        """
        self.model_type = model_type
        # Load the SAM model
        model_path = Path("/app/models/sam_b.pt")
        model_dir = model_path.parent
        
        # Create models directory if it doesn't exist
        model_dir.mkdir(exist_ok=True, parents=True)
        
        if not model_path.exists():
            try:
                logger.info("Model file not found. Attempting to download...")
                import torch
                
                # Download model from Ultralytics
                torch.hub.download_url_to_file(
                    "https://github.com/ultralytics/assets/releases/download/v8.2.0/sam_b.pt",
                    str(model_path)
                )
                logger.info(f"Model downloaded successfully to {model_path}")
            except Exception as e:
                logger.error(f"Failed to download model: {e}")
                logger.warning("Using simulation mode.")
                self.model = None
                return
                
        try:
            self.model = SAM(model_path)
            logger.info(f"SAM model loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.warning("Falling back to simulation mode.")
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
        logger.info(f"SAMModel: _add_point called with ({x}, {y}, {label})")
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
            logger.error(f"Segmentation error: {e}")
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
        logger.info(f"SAMModel predict method called with {len(points or [])} points")
        
        h, w = image.shape[:2]
        result_mask = np.zeros((h, w), dtype=np.uint8)
        
        # CRITICAL FIX: Always reset points and labels for each prediction
        self.points = []
        self.labels = []
        logger.info("SAMModel: Reset points and labels arrays")

        if self.model is None:
            logger.info("SAMModel: Using simulation mode (model not loaded)")
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
        
        # Use the actual model - FIXED IMPLEMENTATION
        if prompt_type == "point" and points:
            logger.info("SAMModel: Processing point prompts with actual SAM model")
            
            # CRITICAL FIX: Properly extract points and labels like Streamlit version
            for x, y, is_positive in points:
                logger.info(f"SAMModel: Adding point ({x}, {y}) with label {1 if is_positive else 0}")
                self._add_point(int(x), int(y), 1 if is_positive else 0)
            
            logger.info(f"SAMModel: Final points: {self.points}")
            logger.info(f"SAMModel: Final labels: {self.labels}")
                
            results = self._run_segmentation(image)
            
            if results and hasattr(results[0], 'masks') and results[0].masks is not None:
                logger.info(f"SAMModel: Got {len(results[0].masks.data)} masks from SAM")
                for i, mask in enumerate(results[0].masks.data):
                    mask_np = mask.cpu().numpy().astype("uint8")
                    logger.info(f"SAMModel: Processing mask {i}, shape: {mask_np.shape}, unique values: {np.unique(mask_np)}")
                    result_mask = np.logical_or(result_mask, mask_np).astype(np.uint8)
            else:
                logger.warning("SAMModel: No masks returned from SAM model")
        
        logger.info(f"SAMModel: Final result mask shape: {result_mask.shape}, non-zero pixels: {np.count_nonzero(result_mask)}")
        return result_mask
        
    def resize_frame(self, frame, target_width=640, target_height=480):
        """
        Resize frame to target dimensions while maintaining aspect ratio
        EXACT REPLICA of Streamlit resize_frame function
        
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
        
        logger.info(f"SAMModel: Resized frame from {w}x{h} to {target_width}x{target_height}")
        logger.info(f"SAMModel: Actual image size: {new_w}x{new_h}, offset: ({x_offset}, {y_offset})")
        
        return canvas

    def predict_from_base64(self, image_data: str, prompt_type: str, points: List[Dict] = None, boxes: List[Dict] = None):
        """
        Predict from base64 encoded image data
        
        Args:
            image_data (str): Base64 encoded image
            prompt_type (str): Type of prompt ('point' or 'box')
            points (List[Dict]): List of point prompts with x, y, is_positive
            boxes (List[Dict]): List of box prompts with x1, y1, x2, y2
            
        Returns:
            tuple: (base64_mask, confidence)
        """
        try:
            logger.info(f"SAMModel: Starting prediction from base64...")
            logger.info(f"SAMModel: Image data length: {len(image_data)}")
            logger.info(f"SAMModel: Prompt type: {prompt_type}")
            logger.info(f"SAMModel: Points: {points}")
            logger.info(f"SAMModel: Boxes: {boxes}")
            
            # Decode image
            image_bytes = base64.b64decode(image_data)
            pil_image = Image.open(BytesIO(image_bytes))
            image_array = np.array(pil_image)
            
            logger.info(f"SAMModel: Decoded image shape: {image_array.shape}")
            logger.info(f"SAMModel: Image dtype: {image_array.dtype}")
            
            # CRITICAL: Resize image to 640x480 like Streamlit (EXACT SAME APPROACH)
            resized_frame = self.resize_frame(image_array, 640, 480)
            logger.info(f"SAMModel: Resized frame shape: {resized_frame.shape}")
            
            # Convert points format (coordinates are already in 640x480 space from frontend)
            if points:
                point_list = [(p['x'], p['y'], p['is_positive']) for p in points]
            else:
                point_list = []
            
            # Convert boxes format  
            if boxes:
                box_list = [(b['x1'], b['y1'], b['x2'], b['y2']) for b in boxes]
            else:
                box_list = []
            
            logger.info(f"SAMModel: Converted points (640x480 coordinates): {point_list}")
            logger.info(f"SAMModel: Converted boxes (640x480 coordinates): {box_list}")
            
            # Run prediction on RESIZED frame (like Streamlit)
            logger.info(f"SAMModel: Calling predict method with resized frame...")
            mask = self.predict(resized_frame, prompt_type, point_list, box_list)
            
            logger.info(f"SAMModel: Prediction completed")
            logger.info(f"SAMModel: Mask shape: {mask.shape}")
            logger.info(f"SAMModel: Mask dtype: {mask.dtype}")
            logger.info(f"SAMModel: Mask unique values: {np.unique(mask)}")
            logger.info(f"SAMModel: Mask non-zero pixels: {np.count_nonzero(mask)}")
            logger.info(f"SAMModel: Total pixels: {mask.size}")
            logger.info(f"SAMModel: Mask coverage: {np.count_nonzero(mask)/mask.size*100:.2f}%")
            
            # ENFORCE: Mask must be 640x480 to match processing resolution
            if mask.shape != (480, 640):
                logger.error(f"Invalid mask shape: {mask.shape}, expected (480, 640)")
                logger.error("This indicates an issue with the SAM model or prediction process")
                # Try to resize mask to correct dimensions if possible
                from PIL import Image as PIL_Image
                mask_pil = PIL_Image.fromarray((mask * 255).astype(np.uint8), mode='L')
                mask_pil = mask_pil.resize((640, 480), PIL_Image.Resampling.NEAREST)
                mask = np.array(mask_pil) / 255.0
                logger.warning(f"Resized mask from {mask.shape} to (480, 640)")
            
            # Encode mask as base64
            mask_image = Image.fromarray(mask * 255, mode='L')
            
            # Validate final mask dimensions
            logger.info(f"SAMModel: Final mask image dimensions: {mask_image.size} (should be 640x480)")
            if mask_image.size != (640, 480):
                logger.error(f"Final mask dimensions incorrect: {mask_image.size}, expected (640, 480)")
            
            buffer = BytesIO()
            mask_image.save(buffer, format='PNG')
            mask_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            logger.info(f"SAMModel: Encoded mask as base64, length: {len(mask_base64)}")
            logger.info(f"SAMModel: Base64 preview: {mask_base64[:50]}...")
            
            return mask_base64, 0.8
            
        except Exception as e:
            logger.error(f"SAMModel prediction error: {e}")
            logger.error(f"SAMModel exception type: {type(e).__name__}")
            import traceback
            logger.error(f"SAMModel full traceback: {traceback.format_exc()}")
            
            # Return empty mask
            logger.warning("SAMModel: Returning empty mask due to error")
            h, w = 100, 100  # Default size
            empty_mask = np.zeros((h, w), dtype=np.uint8)
            mask_image = Image.fromarray(empty_mask, mode='L')
            buffer = BytesIO()
            mask_image.save(buffer, format='PNG')
            mask_base64 = base64.b64encode(buffer.getvalue()).decode()
            logger.info(f"SAMModel: Empty mask base64 length: {len(mask_base64)}")
            return mask_base64, 0.0
        
    def get_contours(self):
        """
        Get the contours of the segmented image
        
        Returns:
            list: Detected contours
        """
        return self.contours
        
    def is_loaded(self):
        """Check if model is loaded and ready"""
        return self.model is not None