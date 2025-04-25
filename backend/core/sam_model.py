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
        
    def add_point(self, x: int, y: int, label: int):
        """Add a new point with its label."""
        self.points.append((x, y))
        self.labels.append(label)
        print(f"Added {'foreground' if label == 1 else 'background'} point at ({x}, {y})")
        
    def run_segmentation(self, image_frame: np.ndarray):
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

    def reset(self):
        """Reset all points."""
        self.points = []
        self.labels = []
        self.result_image = None
        print("Reset all points")

    def save_result(self, output_path: str):
        """WIP: Save the current segmentation result."""

        # TODO-100: save the mask and contours to a file
        if self.result_image is not None:
            cv2.imwrite(output_path, self.result_image)
            print(f"Saved segmentation to {output_path}")
        else:
            print("No segmentation to save")

    def save_yolo_labels(self, image_path: str, image_frame: np.ndarray, video_frame_number: int, sam_results, label: int):
        """Save segmentation results in YOLOv11 format."""
        image_name = os.path.basename(image_path).split('.')[0]
        label_path = os.path.join(os.path.dirname(image_path), image_name + str(video_frame_number) + ".txt")
        
        # Open file to write labels
        with open(label_path, 'w') as label_file:
            height, width, _ = image_frame.shape
            if sam_results and hasattr(sam_results[0], 'masks') and sam_results[0].masks is not None:
                # mask_composite = np.zeros_like(display_image)
                
                for i, mask in enumerate(sam_results[0].masks.data):
                    mask_np = mask.cpu().numpy().astype("uint8") * 255
                    # Color the mask with a semi-transparent overlay
                    # mask_composite[mask_np > 0] = [0, 255, 0]  # Green mask

                    # Draw contours
                    contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # cv2.drawContours(display_image, contours, -1, (0, 255, 0), 2)

                # Normalize points to be between 0 and 1
                normalized_points = []
                for contour in contours:
                    for point in contour:
                        # Normalize each point
                        norm_x = point[0][0] / width
                        norm_y = point[0][1] / height
                        normalized_points.append(f"{norm_x} {norm_y}")

                
                print(f"normalized countours size: {len(normalized_points)}")

                if len(normalized_points) > 2:
                    label_file.write(f"{label} " + " ".join(normalized_points) + "\n")
        
        print(f"Labels saved in YOLO format at {label_path}")




#example usage
def main():
    # Configuration
    # model_path = "../models/sam2.1_b.pt"
    image_path = Path(__file__).parent.parent.parent / "inputs" / "image.jpg"  # Path to your image file
    # image_path = Path(__file__).parent.parent / "inputs" / "image.jpg"

    # Create SAMModel instance
    app = SAMModel()

    # Load the image
    image = cv2.imread(str(image_path))
    # image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image at {image_path}.")
        return

    # Example of adding points: add some points manually (for testing purposes)
    # In a real case, you would probably capture points from user input
    if len(app.points) == 0:  # Add initial points if not added
        app.add_point(100, 100, 1)  # Foreground point
        # app.add_point(200, 200, 0)  # Background point 
    
    # Process the image with segmentation model
    results = app.run_segmentation(image)
    
    if results is None:
        return  # If segmentation failed, exit early

    # Start with a fresh copy of the original for drawing
    display_image = image.copy()

    # Draw masks on the image
    if results and hasattr(results[0], 'masks') and results[0].masks is not None:
        mask_composite = np.zeros_like(display_image)
        
        for i, mask in enumerate(results[0].masks.data):
            mask_np = mask.cpu().numpy().astype("uint8") * 255
            # Color the mask with a semi-transparent overlay
            mask_composite[mask_np > 0] = [0, 255, 0]  # Green mask

            # Draw contours
            contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(display_image, contours, -1, (0, 255, 0), 2)

            print(f"countours: {contours}")
        # Apply mask overlay with transparency
        alpha = 0.4  # Transparency factor
        cv2.addWeighted(mask_composite, alpha, display_image, 1 - alpha, 0, display_image)
        
        # Save result for later
        # TODO-999: change this
        app.result_image = display_image.copy()

    # Draw all points with different colors based on label
    for i, ((x, y), label) in enumerate(zip(app.points, app.labels)):
        color = (0, 0, 255) if label == 1 else (255, 0, 0)  # Red for foreground, Blue for background
        cv2.circle(display_image, (x, y), 5, color, -1)
        cv2.circle(display_image, (x, y), 5, (255, 255, 255), 1)  # White border
    
    # Display the result
    cv2.imshow("Segmented Image", display_image)
    
    # Wait for user input and handle events
    key = cv2.waitKey(0) & 0xFF
    if key == ord('q'):  # Quit
        pass
    elif key == ord('r'):  # Reset points
        app.reset()
    elif key == ord('s'):  # Save result
        # output_path = "../output/segmented_image.png"  # Customize the path as needed
        output_path = Path(__file__).parent.parent.parent / "outputs" / "seg_image.jpg"
        output_path = str(output_path)
        # app.save_result(output_path)
        app.save_yolo_labels(
            image_path=str(image_path),
            image_frame=image, 
            video_frame_number=453, 
            sam_results=results, 
            label=1)  # Save YOLO labels
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
