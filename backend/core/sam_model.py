"""
WIP
"""


import cv2
import os
import numpy as np
from ultralytics import SAM
from typing import Tuple, List, Optional, Dict
from pathlib import Path

class SAMModel:    
    def __init__(self):
        """Initialize the application with the model path."""
        # Load the SAM model
        # TODO-1000:loaded from a config file ?
        model_path = Path(__file__).parent.parent.parent / "models" / "sam2.1_b.pt"
        self.model = SAM(model_path)
        print("Model loaded successfully!")
        
        # Track interaction points
        self.points = []  # (x, y) coordinates
        self.labels = []  # 1 for foreground, 0 for background (we jest need foreground for now)
        self.result_image = None
        
    def _add_point(self, x: int, y: int, label: int=1):
        """Add a new point with its label."""
        self.points.append((x, y))
        self.labels.append(label)
        print(f"Added {'foreground' if label == 1 else 'background'} point at ({x}, {y})")
        
    def _run_segmentation(self, image_frame: np.ndarray)->Optional[List[Dict]]:
        """Run the SAM model with the current points and return the segmentation results."""
        # Ensure that points and labels are the same length
        if len(self.points) != len(self.labels):
            print(f"Error: Number of points ({len(self.points)}) doesn't match number of labels ({len(self.labels)})")
            return None  # Return None if points and labels mismatch
        
        # Run segmentation
        try:
            results = self.model.predict(
                source=image_frame, 
                points=self.points, 
                labels=self.labels, 
                show=False
            )
            return results

        except Exception as e:
            print(f"Segmentation error: {e}")
            return None
    def predict(self, 
                points: List[Tuple[int, int]],
                labels: List[int],
                image_frame: np.ndarray) -> Optional[List[Dict]]:
        """Run the SAM model with the given points and labels."""
        for point, label in zip(points, labels):
            self._add_point(point[0], point[1], label)
        
        return self._run_segmentation(image_frame)

    def save_yolo_labels(self, image_path: str, image_frame: np.ndarray, video_frame_number: int, sam_results, label: int):
        """Save segmentation results in YOLOv11 format."""
        image_name = os.path.basename(image_path).split('.')[0]
        label_path = os.path.join(os.path.dirname(image_path), image_name + str(video_frame_number) + ".txt")
        
        # for debugging: show the segmented image with contours
        # display_image = image_frame.copy()

        # Open file to write labels
        with open(label_path, 'w') as label_file:
            height, width, _ = image_frame.shape
            if sam_results and hasattr(sam_results[0], 'masks') and sam_results[0].masks is not None:
                # mask_composite = np.zeros_like(display_image)
                
                for i, mask in enumerate(sam_results[0].masks.data):
                    mask_np = mask.cpu().numpy().astype("uint8") * 255
                    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # for debugging: show the segmented image with contours
                    # cv2.drawContours(display_image, contours, -1, (0, 255, 0), 2)

                # Normalize points to be between 0 and 1
                normalized_points = []
                for contour in contours:
                    for point in contour:
                        # Normalize each point
                        norm_x = point[0][0] / width
                        norm_y = point[0][1] / height
                        normalized_points.append(f"{norm_x} {norm_y}")

                # For debugging: show the segmented image with contours
                # cv2.imshow("Segmented saved Image", display_image)
                # print(f"normalized countours size: {len(normalized_points)}")

                # key = cv2.waitKey(0) & 0xFF
                # if key == ord('q'):  # Quit
                #     pass
                if len(normalized_points) > 2:
                    label_file.write(f"{label} " + " ".join(normalized_points) + "\n")
        
        print(f"Labels saved in YOLO format at {label_path}")
    
#example usage
