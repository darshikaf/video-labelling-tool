from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class MaskAdjustmentRequest(BaseModel):
    mask_data: str  # Base64 encoded mask
    adjustment_type: Literal["expand", "contract", "smooth"]
    amount: int


class MaskAdjustmentResponse(BaseModel):
    adjusted_mask: str  # Base64 encoded adjusted mask
    processing_time: float


@router.post("/adjust", response_model=MaskAdjustmentResponse)
def adjust_mask(request: MaskAdjustmentRequest):
    """
    Apply morphological operations to adjust mask
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Mask adjustment request: {request.adjustment_type}, amount: {request.amount}")
        
        # Decode base64 mask data
        try:
            mask_bytes = base64.b64decode(request.mask_data)
            mask_image = Image.open(BytesIO(mask_bytes))
            mask_array = np.array(mask_image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid mask data: {str(e)}")
        
        # Convert to grayscale if needed
        if len(mask_array.shape) == 3:
            mask_array = cv2.cvtColor(mask_array, cv2.COLOR_RGB2GRAY)
        
        # Convert to binary mask (threshold at 128)
        _, mask_binary = cv2.threshold(mask_array, 128, 255, cv2.THRESH_BINARY)
        
        logger.info(f"Mask shape: {mask_binary.shape}, unique values: {np.unique(mask_binary)}")
        logger.info(f"Non-zero pixels before adjustment: {np.count_nonzero(mask_binary)}")
        
        # Create kernel for morphological operations
        kernel = np.ones((request.amount, request.amount), np.uint8)
        
        # Apply the requested adjustment
        if request.adjustment_type == "expand":
            # Dilate to expand the mask
            adjusted_mask = cv2.dilate(mask_binary, kernel, iterations=1)
            logger.info("Applied dilation (expand)")
            
        elif request.adjustment_type == "contract":
            # Erode to contract the mask
            adjusted_mask = cv2.erode(mask_binary, kernel, iterations=1)
            logger.info("Applied erosion (contract)")
            
        elif request.adjustment_type == "smooth":
            # Apply opening followed by closing to smooth the mask
            adjusted_mask = cv2.morphologyEx(mask_binary, cv2.MORPH_OPEN, kernel)
            adjusted_mask = cv2.morphologyEx(adjusted_mask, cv2.MORPH_CLOSE, kernel)
            logger.info("Applied morphological opening + closing (smooth)")
        
        else:
            raise HTTPException(status_code=400, detail="Invalid adjustment type")
        
        logger.info(f"Non-zero pixels after adjustment: {np.count_nonzero(adjusted_mask)}")
        
        # Convert back to PIL Image and then to base64
        adjusted_image = Image.fromarray(adjusted_mask, mode='L')
        buffer = BytesIO()
        adjusted_image.save(buffer, format='PNG')
        adjusted_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        processing_time = time.time() - start_time
        logger.info(f"Mask adjustment completed in {processing_time:.3f}s")
        
        return MaskAdjustmentResponse(
            adjusted_mask=adjusted_base64,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mask adjustment failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Mask adjustment failed: {str(e)}")


@router.get("/health")
def masks_health():
    """Health check for mask processing service"""
    return {
        "status": "healthy",
        "service": "mask_processing"
    }