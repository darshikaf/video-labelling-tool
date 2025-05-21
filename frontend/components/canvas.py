import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw

class AnnotationCanvas:
    def __init__(self, width, height):
        """
        Initialize the annotation canvas
        
        Args:
            width (int): Canvas width
            height (int): Canvas height
        """
        self.width = width
        self.height = height
        self.points = []
        self.boxes = []
        self.masks = []
        
    def add_point(self, x, y, is_positive=True):
        """
        Add a point prompt to the canvas
        
        Args:
            x (int): X coordinate
            y (int): Y coordinate
            is_positive (bool): Whether it's a positive or negative point
        """
        self.points.append((x, y, is_positive))
    
    def add_box(self, x1, y1, x2, y2):
        """
        Add a box prompt to the canvas
        
        Args:
            x1, y1 (int): Top-left coordinates
            x2, y2 (int): Bottom-right coordinates
        """
        self.boxes.append((x1, y1, x2, y2))
    
    def clear(self):
        """Clear all annotations"""
        self.points = []
        self.boxes = []
        self.masks = []
    
    def draw_annotations(self, image):
        """
        Draw annotations on the image
        
        Args:
            image (numpy.ndarray): Image to draw on
            
        Returns:
            numpy.ndarray: Image with annotations
        """
        result = image.copy()
        
        # Convert to PIL for easier drawing
        pil_image = Image.fromarray(result)
        draw = ImageDraw.Draw(pil_image)
        
        # Draw points
        for x, y, is_positive in self.points:
            color = (0, 255, 0) if is_positive else (255, 0, 0)
            draw.ellipse((x-5, y-5, x+5, y+5), fill=color)
            
        # Draw boxes
        for x1, y1, x2, y2 in self.boxes:
            draw.rectangle((x1, y1, x2, y2), outline=(255, 255, 0), width=2)
        
        # Draw masks if any
        result = np.array(pil_image)
        for mask in self.masks:
            # Apply mask as a colored overlay
            colored_mask = np.zeros_like(result)
            colored_mask[:,:,1] = mask * 255  # Green channel
            
            # Blend with reduced opacity
            alpha = 0.5
            cv2.addWeighted(result, 1, colored_mask, alpha, 0, result)
            
        return result
    
    def generate_mask(self, sam_model, image, prompt_type="point"):
        """
        Generate a segmentation mask using SAM model
        
        Args:
            sam_model: SAM model instance
            image: Input image
            prompt_type: Type of prompt to use
            
        Returns:
            numpy.ndarray: Binary mask
        """
        if prompt_type == "point" and self.points:
            return sam_model.predict(image, prompt_type="point", points=self.points)
        elif prompt_type == "box" and self.boxes:
            return sam_model.predict(image, prompt_type="box", boxes=self.boxes)
        else:
            return None
