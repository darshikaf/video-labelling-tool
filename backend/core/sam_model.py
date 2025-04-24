import cv2
import os
import numpy as np
from ultralytics import SAM
from typing import Tuple, List, Optional, Dict

class SAMModel:    
    def __init__(self):
        """Initialize the application with the model path."""
        # Load the SAM model
        model_path = "../models/sam2.1_b.pt"
        self.model = SAM(model_path)
        print("Model loaded successfully!")
        
        # Track interaction points
        self.points = []  # (x, y) coordinates
        self.labels = []  # 1 for foreground, 0 for background
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
        """Save the current segmentation result."""

        # TODO-1000: save the mask and contours to a file
        if self.result_image is not None:
            cv2.imwrite(output_path, self.result_image)
            print(f"Saved segmentation to {output_path}")
        else:
            print("No segmentation to save")


#example usage
def main():
    # Configuration
    # model_path = "../models/sam2.1_b.pt"
    image_path = "../inputs/image.jpg"  # Path to your image file

    # Create SAMModel instance
    app = SAMModel()

    # Load the image
    image = cv2.imread(image_path)
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
        output_path = "../output/segmented_image.png"  # Customize the path as needed
        app.save_result(output_path)
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
