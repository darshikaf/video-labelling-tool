import os
import time
import logging
import hashlib
from pathlib import Path
from typing import Optional
import numpy as np
import cv2
from ultralytics import SAM
import redis
import pickle

from schemas import SAMPredictionRequest, SAMPredictionResponse

logger = logging.getLogger(__name__)


class SAMPredictor:
    def __init__(self):
        self.model: Optional[SAM] = None
        self.redis_client: Optional[redis.Redis] = None
        self.model_path = Path("/app/models/sam_b.pt")
        self.cache_enabled = True
        
    async def initialize(self):
        """Initialize the SAM model and Redis connection"""
        try:
            # Initialize Redis connection
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/1")
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            await self._test_redis_connection()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.cache_enabled = False
        
        # Load SAM model
        await self._load_model()
        
    async def _test_redis_connection(self):
        """Test Redis connection"""
        if self.redis_client:
            self.redis_client.ping()
    
    async def _load_model(self):
        """Load the SAM model"""
        try:
            if not self.model_path.exists():
                await self._download_model()
            
            logger.info(f"Loading SAM model from {self.model_path}")
            self.model = SAM(str(self.model_path))
            logger.info("SAM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load SAM model: {e}")
            # Fall back to simulation mode
            logger.warning("Falling back to simulation mode")
            self.model = None
    
    async def _download_model(self):
        """Download SAM model if not present"""
        import torch
        
        logger.info("SAM model not found. Downloading...")
        self.model_path.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            # Download the supported SAM base model
            torch.hub.download_url_to_file(
                "https://github.com/ultralytics/assets/releases/download/v8.2.0/sam_b.pt",
                str(self.model_path)
            )
            logger.info("SAM model downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download SAM model: {e}")
            raise
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None
    
    async def predict(self, request: SAMPredictionRequest) -> SAMPredictionResponse:
        """Run SAM prediction"""
        start_time = time.time()
        
        # Get image
        image = request.get_image()
        image_array = np.array(image)
        
        # Skip caching for now to debug performance issues
        # cached_result = None
        # if self.cache_enabled and request.cache_key:
        #     cached_result = await self._get_cached_prediction(request)
        #     if cached_result:
        #         cached_result.cached = True
        #         return cached_result
        
        # Run prediction
        if self.model is None:
            # Simulation mode
            mask = self._simulate_prediction(image_array, request)
            confidence = 0.8
        else:
            # Real SAM prediction
            mask, confidence = self._run_sam_prediction(image_array, request)
        
        processing_time = time.time() - start_time
        
        # Create response
        response = SAMPredictionResponse(
            mask=SAMPredictionResponse.encode_mask(mask),
            confidence=confidence,
            processing_time=processing_time,
            cached=False
        )
        
        # Skip caching for now
        # if self.cache_enabled and request.cache_key:
        #     await self._cache_prediction(request, response)
        
        return response
    
    def _simulate_prediction(self, image: np.ndarray, request: SAMPredictionRequest) -> tuple[np.ndarray, float]:
        """Simulate SAM prediction for development/testing"""
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        if request.prompt_type == "point" and request.points:
            # Create circular masks around points
            for point in request.points:
                if point.is_positive:
                    radius = min(h, w) // 8
                    cv2.circle(mask, (int(point.x), int(point.y)), radius, 1, -1)
                    
        elif request.prompt_type == "box" and request.boxes:
            # Create rectangular masks from boxes
            for box in request.boxes:
                cv2.rectangle(
                    mask,
                    (int(box.x1), int(box.y1)),
                    (int(box.x2), int(box.y2)),
                    1,
                    -1
                )
        
        return mask, 0.8
    
    def _run_sam_prediction(self, image: np.ndarray, request: SAMPredictionRequest) -> tuple[np.ndarray, float]:
        """Run actual SAM prediction"""
        try:
            if request.prompt_type == "point":
                # Convert points to SAM format (using tuples as in Streamlit)
                points = []
                labels = []
                for point in request.points or []:
                    points.append((int(point.x), int(point.y)))
                    labels.append(1 if point.is_positive else 0)
                
                # Run prediction using correct Ultralytics API
                results = self.model.predict(source=image, points=points, labels=labels, show=False)
                
            elif request.prompt_type == "box":
                # Convert boxes to SAM format  
                boxes = []
                for box in request.boxes or []:
                    boxes.append([box.x1, box.y1, box.x2, box.y2])
                
                # Run prediction using correct Ultralytics API
                results = self.model.predict(source=image, bboxes=boxes, show=False)
            
            else:
                raise ValueError(f"Unsupported prompt type: {request.prompt_type}")
            
            # Extract mask from results
            if results and hasattr(results[0], 'masks') and results[0].masks is not None:
                # Get the first mask
                mask_tensor = results[0].masks.data[0]
                if hasattr(mask_tensor, 'cpu'):
                    mask = mask_tensor.cpu().numpy().astype(np.uint8)
                else:
                    mask = mask_tensor.astype(np.uint8)
                
                # Get confidence if available (SAM doesn't always provide confidence scores)
                confidence = 0.8  # Default confidence for SAM masks
                
                return mask, confidence
            else:
                # Return empty mask if no results
                h, w = image.shape[:2]
                return np.zeros((h, w), dtype=np.uint8), 0.0
                
        except Exception as e:
            logger.error(f"SAM prediction error: {e}")
            # Fall back to simulation
            return self._simulate_prediction(image, request)
    
    def _get_cache_key(self, request: SAMPredictionRequest) -> str:
        """Generate cache key for request"""
        # Create hash of image data and prompts
        content = f"{request.image_data}_{request.prompt_type}"
        if request.points:
            points_str = "_".join([f"{p.x},{p.y},{p.is_positive}" for p in request.points])
            content += f"_points_{points_str}"
        if request.boxes:
            boxes_str = "_".join([f"{b.x1},{b.y1},{b.x2},{b.y2}" for b in request.boxes])
            content += f"_boxes_{boxes_str}"
        
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_cached_prediction(self, request: SAMPredictionRequest) -> Optional[SAMPredictionResponse]:
        """Get prediction from cache"""
        if not self.cache_enabled or not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(request)
            cached_data = self.redis_client.get(f"sam_prediction:{cache_key}")
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    async def _cache_prediction(self, request: SAMPredictionRequest, response: SAMPredictionResponse):
        """Cache prediction result"""
        if not self.cache_enabled or not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(request)
            # Cache for 1 hour
            self.redis_client.setex(
                f"sam_prediction:{cache_key}",
                3600,
                pickle.dumps(response)
            )
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    async def clear_cache(self, cache_key: str):
        """Clear specific cache entry"""
        if not self.cache_enabled or not self.redis_client:
            return
        
        try:
            self.redis_client.delete(f"sam_prediction:{cache_key}")
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")