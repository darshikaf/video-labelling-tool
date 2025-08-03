"""
Annotation format converters for different training formats (YOLO, COCO, Pascal VOC)
"""
import json
import base64
import io
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
from datetime import datetime

try:
    import numpy as np
    import cv2
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class AnnotationFormatConverter:
    """Base class for annotation format converters"""
    
    def __init__(self, image_width: int, image_height: int):
        self.image_width = image_width
        self.image_height = image_height
    
    def mask_to_polygon(self, mask_data: str) -> List[List[int]]:
        """Convert base64 mask to polygon coordinates"""
        if not DEPENDENCIES_AVAILABLE:
            print("Warning: numpy/cv2 not available - using fallback polygon generation")
            return self._fallback_polygon_from_mask(mask_data)
            
        try:
            # Decode base64 mask
            if mask_data.startswith('data:image'):
                mask_data = mask_data.split(',')[1]
            
            mask_bytes = base64.b64decode(mask_data)
            
            # Convert to PIL Image and then numpy array
            mask_image = Image.open(io.BytesIO(mask_bytes))
            mask_array = np.array(mask_image)
            
            # Convert to binary mask (handle both grayscale and RGB)
            if len(mask_array.shape) == 3:
                # If RGB, convert to grayscale
                mask_array = np.dot(mask_array[...,:3], [0.2989, 0.5870, 0.1140])
            
            # Threshold to binary
            binary_mask = (mask_array > 128).astype(np.uint8) * 255
            
            # Find contours
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            polygons = []
            for contour in contours:
                # Simplify contour and convert to list of [x, y] points
                epsilon = 0.005 * cv2.arcLength(contour, True)
                simplified = cv2.approxPolyDP(contour, epsilon, True)
                
                polygon = []
                for point in simplified:
                    x, y = point[0]
                    polygon.extend([int(x), int(y)])
                
                if len(polygon) >= 6:  # At least 3 points (6 coordinates)
                    polygons.append(polygon)
            
            return polygons
            
        except Exception as e:
            print(f"Error converting mask to polygon: {e}")
            return self._fallback_polygon_from_mask(mask_data)
    
    def _fallback_polygon_from_mask(self, mask_data: str) -> List[List[int]]:
        """Fallback polygon generation when cv2/numpy not available"""
        try:
            # Simple bounding box approximation using PIL only
            if mask_data.startswith('data:image'):
                mask_data = mask_data.split(',')[1]
            
            mask_bytes = base64.b64decode(mask_data)
            mask_image = Image.open(io.BytesIO(mask_bytes))
            
            # Get image dimensions
            width, height = mask_image.size
            
            # Create approximate polygon from center area (fallback)
            center_x, center_y = width // 2, height // 2
            margin = min(width, height) // 4
            
            # Simple rectangle polygon
            polygon = [
                center_x - margin, center_y - margin,  # top-left
                center_x + margin, center_y - margin,  # top-right
                center_x + margin, center_y + margin,  # bottom-right
                center_x - margin, center_y + margin   # bottom-left
            ]
            
            return [polygon]
            
        except Exception as e:
            print(f"Fallback polygon generation failed: {e}")
            # Return minimal valid polygon
            return [[100, 100, 200, 100, 200, 200, 100, 200]]
    
    def mask_to_bbox(self, mask_data: str) -> Optional[List[int]]:
        """Convert base64 mask to bounding box [x, y, width, height]"""
        try:
            polygons = self.mask_to_polygon(mask_data)
            if not polygons:
                return None
            
            # Find bounding box from all polygons
            all_points = []
            for polygon in polygons:
                for i in range(0, len(polygon), 2):
                    all_points.append([polygon[i], polygon[i+1]])
            
            if not all_points:
                return None
            
            if DEPENDENCIES_AVAILABLE:
                all_points_array = np.array(all_points)
                x_min, y_min = np.min(all_points_array, axis=0)
                x_max, y_max = np.max(all_points_array, axis=0)
            else:
                # Fallback without numpy
                x_coords = [point[0] for point in all_points]
                y_coords = [point[1] for point in all_points]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
            
            return [int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)]
            
        except Exception as e:
            print(f"Error converting mask to bbox: {e}")
            return None


class YOLOConverter(AnnotationFormatConverter):
    """Convert annotations to YOLO format"""
    
    def convert(self, annotation_data: Dict[str, Any]) -> str:
        """
        Convert annotation to YOLO format string
        Format: class_id center_x center_y width height
        Coordinates are normalized (0-1)
        """
        try:
            category_id = annotation_data.get('category_id', 0)
            mask_data = annotation_data.get('mask_data', '')
            
            if not mask_data:
                return ""
            
            # Get bounding box
            bbox = self.mask_to_bbox(mask_data)
            if not bbox:
                return ""
            
            x, y, w, h = bbox
            
            # Convert to YOLO format (normalized center coordinates)
            center_x = (x + w / 2) / self.image_width
            center_y = (y + h / 2) / self.image_height
            norm_width = w / self.image_width
            norm_height = h / self.image_height
            
            # YOLO format: class_id center_x center_y width height
            return f"{category_id - 1} {center_x:.6f} {center_y:.6f} {norm_width:.6f} {norm_height:.6f}"
            
        except Exception as e:
            print(f"Error converting to YOLO format: {e}")
            return ""


class COCOConverter(AnnotationFormatConverter):
    """Convert annotations to COCO format"""
    
    def __init__(self, image_width: int, image_height: int):
        super().__init__(image_width, image_height)
        self.annotation_id = 1
    
    def convert(self, annotation_data: Dict[str, Any], image_id: int = 1) -> Dict[str, Any]:
        """
        Convert annotation to COCO format dict
        """
        try:
            category_id = annotation_data.get('category_id', 1)
            mask_data = annotation_data.get('mask_data', '')
            
            if not mask_data:
                return {}
            
            # Get polygon and bounding box
            polygons = self.mask_to_polygon(mask_data)
            bbox = self.mask_to_bbox(mask_data)
            
            if not polygons or not bbox:
                return {}
            
            # Calculate area (approximate from bounding box)
            area = bbox[2] * bbox[3]
            
            coco_annotation = {
                "id": self.annotation_id,
                "image_id": image_id,
                "category_id": category_id,
                "segmentation": polygons,
                "area": area,
                "bbox": bbox,  # [x, y, width, height]
                "iscrowd": 0
            }
            
            self.annotation_id += 1
            return coco_annotation
            
        except Exception as e:
            print(f"Error converting to COCO format: {e}")
            return {}
    
    def create_coco_structure(self, annotations: List[Dict], categories: List[Dict], 
                            image_info: Dict) -> Dict[str, Any]:
        """Create complete COCO dataset structure"""
        return {
            "info": {
                "description": "Medical Video Annotation Dataset",
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "Medical Video Annotation Tool",
                "date_created": datetime.now().isoformat()
            },
            "licenses": [
                {
                    "id": 1,
                    "name": "Custom License",
                    "url": ""
                }
            ],
            "images": [image_info],
            "annotations": annotations,
            "categories": categories
        }


class PascalVOCConverter(AnnotationFormatConverter):
    """Convert annotations to Pascal VOC XML format"""
    
    def convert(self, annotation_data: Dict[str, Any], image_filename: str) -> str:
        """
        Convert annotation to Pascal VOC XML format string
        """
        try:
            category_name = annotation_data.get('category_name', 'object')
            mask_data = annotation_data.get('mask_data', '')
            
            if not mask_data:
                return ""
            
            # Get bounding box
            bbox = self.mask_to_bbox(mask_data)
            if not bbox:
                return ""
            
            x, y, w, h = bbox
            x_min, y_min = x, y
            x_max, y_max = x + w, y + h
            
            xml_content = f"""<annotation>
    <folder>images</folder>
    <filename>{image_filename}</filename>
    <path>{image_filename}</path>
    <source>
        <database>Medical Video Annotation</database>
    </source>
    <size>
        <width>{self.image_width}</width>
        <height>{self.image_height}</height>
        <depth>3</depth>
    </size>
    <segmented>1</segmented>
    <object>
        <name>{category_name}</name>
        <pose>Unspecified</pose>
        <truncated>0</truncated>
        <difficult>0</difficult>
        <bndbox>
            <xmin>{x_min}</xmin>
            <ymin>{y_min}</ymin>
            <xmax>{x_max}</xmax>
            <ymax>{y_max}</ymax>
        </bndbox>
    </object>
</annotation>"""
            
            return xml_content
            
        except Exception as e:
            print(f"Error converting to Pascal VOC format: {e}")
            return ""


class AnnotationFormatService:
    """Service to handle different annotation formats"""
    
    def __init__(self, image_width: int = 640, image_height: int = 480):
        self.image_width = image_width
        self.image_height = image_height
    
    def get_converter(self, format_type: str):
        """Get the appropriate converter for the format"""
        converters = {
            'YOLO': YOLOConverter,
            'COCO': COCOConverter,
            'PASCAL_VOC': PascalVOCConverter
        }
        
        converter_class = converters.get(format_type.upper())
        if not converter_class:
            raise ValueError(f"Unsupported format: {format_type}")
        
        return converter_class(self.image_width, self.image_height)
    
    def convert_annotation(self, annotation_data: Dict[str, Any], format_type: str, 
                         **kwargs) -> str:
        """Convert annotation to specified format"""
        converter = self.get_converter(format_type)
        
        if format_type.upper() == 'COCO':
            # COCO returns dict, need to serialize
            result = converter.convert(annotation_data, **kwargs)
            return json.dumps(result, indent=2) if result else ""
        else:
            # YOLO and Pascal VOC return strings
            return converter.convert(annotation_data, **kwargs)
    
    def get_file_extension(self, format_type: str) -> str:
        """Get appropriate file extension for format"""
        extensions = {
            'YOLO': '.txt',
            'COCO': '.json', 
            'PASCAL_VOC': '.xml'
        }
        return extensions.get(format_type.upper(), '.txt')


# Global service instance
annotation_format_service = AnnotationFormatService()