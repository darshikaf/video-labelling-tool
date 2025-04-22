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
            
        return np.array(pil_image)
