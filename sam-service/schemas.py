from typing import List, Optional
from pydantic import BaseModel, validator
import base64
import io
from PIL import Image


class PointPrompt(BaseModel):
    x: float
    y: float
    is_positive: bool = True


class BoxPrompt(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class SAMPredictionRequest(BaseModel):
    image_data: str  # Base64 encoded image
    prompt_type: str  # "point" or "box"
    points: Optional[List[PointPrompt]] = None
    boxes: Optional[List[BoxPrompt]] = None
    cache_key: Optional[str] = None  # For caching image encodings
    
    @validator('prompt_type')
    def validate_prompt_type(cls, v):
        if v not in ['point', 'box']:
            raise ValueError('prompt_type must be either "point" or "box"')
        return v
    
    @validator('points')
    def validate_points(cls, v, values):
        if values.get('prompt_type') == 'point' and (not v or len(v) == 0):
            raise ValueError('points required for point prompt type')
        return v
    
    @validator('boxes')
    def validate_boxes(cls, v, values):
        if values.get('prompt_type') == 'box' and (not v or len(v) == 0):
            raise ValueError('boxes required for box prompt type')
        return v
    
    def get_image(self) -> Image.Image:
        """Decode base64 image data to PIL Image"""
        try:
            image_bytes = base64.b64decode(self.image_data)
            image = Image.open(io.BytesIO(image_bytes))
            return image.convert('RGB')
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}")


class SAMPredictionResponse(BaseModel):
    mask: str  # Base64 encoded binary mask
    confidence: float
    processing_time: float
    cached: bool = False
    
    @staticmethod
    def encode_mask(mask_array) -> str:
        """Encode numpy mask array to base64 string"""
        import numpy as np
        if mask_array.dtype != np.uint8:
            mask_array = (mask_array * 255).astype(np.uint8)
        
        # Convert to PIL Image and then to base64
        mask_image = Image.fromarray(mask_array, mode='L')
        buffer = io.BytesIO()
        mask_image.save(buffer, format='PNG')
        mask_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return mask_b64


class HealthResponse(BaseModel):
    message: str
    status: str
    model_loaded: bool
    timestamp: float