from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

from core.sam_predictor import SAMPredictor
from schemas import SAMPredictionRequest, SAMPredictionResponse, HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SAM Inference Service",
    description="Ultralytics SAM service for video annotation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sam_predictor = SAMPredictor()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting SAM service...")
    try:
        await sam_predictor.initialize()
        logger.info("SAM model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to initialize SAM model: {e}")
        raise

@app.get("/", response_model=HealthResponse)
async def root():
    return HealthResponse(
        message="SAM Inference Service",
        status="healthy",
        model_loaded=sam_predictor.is_loaded(),
        timestamp=time.time()
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        message="SAM Inference Service",
        status="healthy" if sam_predictor.is_loaded() else "unhealthy",
        model_loaded=sam_predictor.is_loaded(),
        timestamp=time.time()
    )

@app.post("/predict", response_model=SAMPredictionResponse)
async def predict_mask(request: SAMPredictionRequest):
    if not sam_predictor.is_loaded():
        raise HTTPException(status_code=503, detail="SAM model not loaded")
    
    try:
        result = await sam_predictor.predict(request)
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/batch")
async def predict_batch(requests: list[SAMPredictionRequest]):
    if not sam_predictor.is_loaded():
        raise HTTPException(status_code=503, detail="SAM model not loaded")
    
    try:
        results = []
        for request in requests:
            result = await sam_predictor.predict(request)
            results.append(result)
        return {"results": results}
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@app.delete("/cache/{cache_key}")
async def clear_cache(cache_key: str):
    try:
        await sam_predictor.clear_cache(cache_key)
        return {"message": f"Cache cleared for key: {cache_key}"}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")