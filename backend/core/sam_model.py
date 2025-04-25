import numpy as np
import cv2

class SAMModel:
    """
    Simple placeholder for SAM model integration
    In a real implementation, this would use the Segment Anything model
    """
    def __init__(self, model_type="vit_h"):
        self.model_type = model_type
        print(f"[SIMULATION] Initializing SAM model of type {model_type}")
        # In a real implementation, we would load the SAM model here
        
    def predict(self, image, prompt_type="point", points=None, boxes=None, masks=None):
        """
        Simulate SAM prediction (for MVP demo)
        
        Args:
            image: Input image
            prompt_type: Type of prompt (point, box, mask)
            points: List of point prompts [(x, y, is_positive), ...]
            boxes: List of box prompts
            masks: List of mask prompts
            
        Returns:
            numpy.ndarray: Binary mask
        """
        # For the MVP, create a circular mask around clicked point
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        if prompt_type == "point" and points and len(points) > 0:
            # Use clicked points as centroids for masks
            for x, y, is_positive in points:
                if is_positive:
                    # Create a circular mask centered at the clicked point
                    radius = np.random.randint(min(h, w) // 8, min(h, w) // 4)
                    cv2.circle(mask, (int(x), int(y)), radius, 1, -1)
        elif prompt_type == "center-point":
            # Original behavior - create mask at center
            center_x, center_y = w // 2, h // 2
            cv2.circle(mask, (center_x, center_y), min(h, w) // 4, 1, -1)
        else:
            # Random blob placeholder behavior
            for _ in range(3):
                cx = np.random.randint(w//4, 3*w//4)
                cy = np.random.randint(h//4, 3*h//4)
                radius = np.random.randint(min(h, w) // 8, min(h, w) // 3)
                cv2.circle(mask, (cx, cy), radius, 1, -1)
                
        return mask