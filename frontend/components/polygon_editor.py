import cv2
import numpy as np
from PIL import Image
import streamlit as st
import math

class PolygonEditor:
    """
    Component for editing mask outlines as polygons
    """
    def __init__(self):
        """Initialize the polygon editor"""
        self.polygon_points = []  # List of [x, y] points
        self.selected_node = None
        self.node_radius = 5
        self.edge_distance_threshold = 10  # Max distance to detect edge click
    
    def mask_to_polygon(self, mask):
        """
        Convert binary mask to polygon representation
        
        Args:
            mask (numpy.ndarray): Binary mask
            
        Returns:
            list: List of [x, y] points forming the polygon
        """
        if mask is None:
            return []
            
        # Ensure mask is binary and uint8
        mask_uint8 = mask.astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        # Get the largest contour by area
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Simplify the contour to reduce number of points
        epsilon = 0.002 * cv2.arcLength(largest_contour, True)
        approx_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # Convert to list of [x, y] points
        points = approx_contour.reshape(-1, 2).tolist()
        
        return points
    
    def polygon_to_mask(self, points, shape):
        """
        Convert polygon points to binary mask
        
        Args:
            points (list): List of [x, y] points
            shape (tuple): Shape of the target mask (height, width)
            
        Returns:
            numpy.ndarray: Binary mask
        """
        if len(points) < 3:
            return np.zeros(shape, dtype=np.uint8)
            
        # Create empty mask
        mask = np.zeros(shape, dtype=np.uint8)
        
        # Convert points to numpy array
        points_array = np.array(points, dtype=np.int32)
        
        # Fill polygon
        cv2.fillPoly(mask, [points_array], 1)
        
        return mask
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """
        Calculate the distance from point (px,py) to line segment (x1,y1)-(x2,y2)
        
        Args:
            px, py: Point coordinates
            x1, y1, x2, y2: Line segment coordinates
            
        Returns:
            tuple: (distance, t) where t is the parametric position along the line
        """
        # Line vector
        dx = x2 - x1
        dy = y2 - y1
        
        # Line length squared
        line_len_sq = dx*dx + dy*dy
        
        # If line is a point, return distance to that point
        if line_len_sq == 0:
            return math.sqrt((px-x1)**2 + (py-y1)**2), 0
        
        # Project point onto line
        t = ((px-x1)*dx + (py-y1)*dy) / line_len_sq
        
        if t < 0:
            # Point is before line segment
            return math.sqrt((px-x1)**2 + (py-y1)**2), 0
        elif t > 1:
            # Point is after line segment
            return math.sqrt((px-x2)**2 + (py-y2)**2), 1
        else:
            # Point is alongside the line segment
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            return math.sqrt((px-proj_x)**2 + (py-proj_y)**2), t
    
    def find_nearest_edge(self, x, y, threshold=None):
        """
        Find the nearest edge to the given point
        
        Args:
            x, y: Point coordinates
            threshold: Max distance to consider (or None for no limit)
            
        Returns:
            tuple: (edge_index, parametric_position) or None if no edge found
        """
        if len(self.polygon_points) < 2:
            return None
            
        if threshold is None:
            threshold = self.edge_distance_threshold
            
        min_dist = float('inf')
        nearest_edge = None
        nearest_t = 0
        
        # Check each edge (connecting consecutive points)
        for i in range(len(self.polygon_points)):
            p1 = self.polygon_points[i]
            p2 = self.polygon_points[(i+1) % len(self.polygon_points)]
            
            dist, t = self.point_to_line_distance(x, y, p1[0], p1[1], p2[0], p2[1])
            
            if dist < min_dist and dist < threshold:
                min_dist = dist
                nearest_edge = i
                nearest_t = t
        
        return (nearest_edge, nearest_t) if nearest_edge is not None else None
    
    def find_nearest_node(self, x, y, threshold=None):
        """
        Find the nearest node to the given point
        
        Args:
            x, y: Point coordinates
            threshold: Max distance to consider (or None for no limit)
            
        Returns:
            int: Index of the nearest node or None if no node found
        """
        if not self.polygon_points:
            return None
            
        if threshold is None:
            threshold = self.node_radius * 2
            
        min_dist = float('inf')
        nearest_node = None
        
        # Check each node
        for i, point in enumerate(self.polygon_points):
            dist = math.sqrt((x-point[0])**2 + (y-point[1])**2)
            
            if dist < min_dist and dist < threshold:
                min_dist = dist
                nearest_node = i
        
        return nearest_node

    def add_node_at_edge(self, edge_index, t):
        """
        Add a new node at the specified position along an edge
        
        Args:
            edge_index: Index of the edge
            t: Parametric position along the edge (0-1)
            
        Returns:
            int: Index of the newly inserted node
        """
        if edge_index is None or edge_index < 0 or edge_index >= len(self.polygon_points):
            return None
            
        p1 = self.polygon_points[edge_index]
        p2 = self.polygon_points[(edge_index+1) % len(self.polygon_points)]
        
        # Interpolate point position
        new_x = p1[0] + t * (p2[0] - p1[0])
        new_y = p1[1] + t * (p2[1] - p1[1])
        
        # Insert new node after edge_index
        new_idx = edge_index + 1
        self.polygon_points.insert(new_idx, [new_x, new_y])
        
        return new_idx
    
    def move_node(self, node_index, new_x, new_y):
        """
        Move a node to a new position
        
        Args:
            node_index: Index of the node to move
            new_x, new_y: New position
        """
        if node_index is None or node_index < 0 or node_index >= len(self.polygon_points):
            return
            
        self.polygon_points[node_index] = [new_x, new_y]
    
    def delete_node(self, node_index):
        """
        Delete a node from the polygon
        
        Args:
            node_index: Index of the node to delete
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        if node_index is None or node_index < 0 or node_index >= len(self.polygon_points):
            return False
            
        # Don't delete if we'd have fewer than 3 points
        if len(self.polygon_points) <= 3:
            return False
            
        self.polygon_points.pop(node_index)
        return True
    
    def render_polygon(self, frame):
        """
        Render the polygon on the given frame
        
        Args:
            frame: Image frame to render on
            
        Returns:
            numpy.ndarray: Frame with polygon rendering
        """
        if not self.polygon_points or len(self.polygon_points) < 2:
            return frame
            
        # Create a copy of the frame
        result = frame.copy()
        
        # Draw edges
        points_array = np.array(self.polygon_points, dtype=np.int32)
        cv2.polylines(result, [points_array], True, (0, 255, 0), 2)
        
        # Draw nodes
        for point in self.polygon_points:
            cv2.circle(result, (int(point[0]), int(point[1])), self.node_radius, (255, 0, 0), -1)
            
        return result
