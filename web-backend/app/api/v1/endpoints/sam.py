from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import time
import logging

from app.core.sam_model import SAMModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Global SAM model instance
sam_model: Optional[SAMModel] = None


class PointPrompt(BaseModel):
    x: float
    y: float
    is_positive: bool


class BoxPrompt(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class SAMPredictionRequest(BaseModel):
    image_data: str
    prompt_type: str
    points: Optional[List[PointPrompt]] = None
    boxes: Optional[List[BoxPrompt]] = None


class SAMPredictionResponse(BaseModel):
    mask: str
    confidence: float
    processing_time: float
    cached: bool = False


def get_sam_model():
    """Get or initialize the SAM model"""
    global sam_model
    if sam_model is None:
        logger.info("Initializing SAM model...")
        sam_model = SAMModel()
        logger.info("SAM model initialized")
    return sam_model


@router.get("/health")
def sam_health():
    """SAM service health check"""
    model = get_sam_model()
    return {
        "status": "healthy" if model.is_loaded() else "unhealthy",
        "model_loaded": model.is_loaded(),
        "timestamp": time.time()
    }


@router.post("/predict", response_model=SAMPredictionResponse)
def predict_sam(request: SAMPredictionRequest):
    """Run SAM prediction"""
    start_time = time.time()
    
    logger.info(f"SAM prediction request received:")
    logger.info(f"  - Image data length: {len(request.image_data) if request.image_data else 0}")
    logger.info(f"  - Prompt type: {request.prompt_type}")
    logger.info(f"  - Points count: {len(request.points) if request.points else 0}")
    logger.info(f"  - Boxes count: {len(request.boxes) if request.boxes else 0}")
    
    if request.points:
        for i, p in enumerate(request.points):
            logger.info(f"  - Point {i+1}: ({p.x:.1f}, {p.y:.1f}) positive={p.is_positive}")
    
    try:
        model = get_sam_model()
        
        if not model.is_loaded():
            logger.error("SAM model not loaded")
            raise HTTPException(status_code=503, detail="SAM model not loaded")
        
        logger.info("SAM model is loaded, proceeding with prediction...")
        
        # Convert request format
        points = []
        if request.points:
            points = [{"x": p.x, "y": p.y, "is_positive": p.is_positive} for p in request.points]
        
        boxes = []
        if request.boxes:
            boxes = [{"x1": b.x1, "y1": b.y1, "x2": b.x2, "y2": b.y2} for b in request.boxes]
        
        logger.info(f"Calling SAM model predict_from_base64...")
        
        # Run prediction
        mask_base64, confidence = model.predict_from_base64(
            request.image_data,
            request.prompt_type,
            points,
            boxes
        )
        
        processing_time = time.time() - start_time
        
        logger.info(f"SAM prediction completed:")
        logger.info(f"  - Processing time: {processing_time:.2f}s")
        logger.info(f"  - Confidence: {confidence}")
        logger.info(f"  - Mask data length: {len(mask_base64) if mask_base64 else 0}")
        logger.info(f"  - Mask data preview: {mask_base64[:50] if mask_base64 else 'None'}...")
        
        # Validate mask data
        if not mask_base64:
            logger.warning("WARNING: Empty mask returned from SAM model")
        elif len(mask_base64) < 100:
            logger.warning(f"WARNING: Suspiciously short mask data: {len(mask_base64)} chars")
        
        return SAMPredictionResponse(
            mask=mask_base64,
            confidence=confidence,
            processing_time=processing_time,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"SAM prediction failed with exception: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")