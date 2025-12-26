import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.database import SessionLocal, engine
from app.models import models

# Configure logging for detailed SAM debugging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)


def seed_system_templates():
    """Seed system category templates if they don't exist"""
    db = SessionLocal()
    try:
        # Check if templates already exist
        existing = (
            db.query(models.CategoryTemplate)
            .filter(models.CategoryTemplate.is_system.is_(True))
            .count()
        )

        if existing > 0:
            logger.info(
                f"System templates already exist ({existing} found), skipping seed"
            )
            return

        logger.info("Seeding system category templates...")

        # Surgical Instruments template
        surgical_template = models.CategoryTemplate(
            name="Surgical Instruments",
            description="Common surgical instruments used in laparoscopic procedures",
            is_system=True,
            created_by=None,
        )
        db.add(surgical_template)
        db.flush()

        surgical_items = [
            ("Forceps", "#FF6B6B"),
            ("Scissors", "#4ECDC4"),
            ("Grasper", "#45B7D1"),
            ("Needle Driver", "#96CEB4"),
            ("Retractor", "#FFEAA7"),
            ("Clip Applier", "#DDA0DD"),
            ("Suction", "#98D8C8"),
            ("Cautery", "#F7DC6F"),
        ]

        for i, (name, color) in enumerate(surgical_items):
            item = models.TemplateCategoryItem(
                template_id=surgical_template.id,
                name=name,
                color=color,
                order=i,
            )
            db.add(item)

        # Anatomy template
        anatomy_template = models.CategoryTemplate(
            name="Anatomy - Laparoscopic",
            description="Anatomical structures commonly seen in laparoscopic surgery",
            is_system=True,
            created_by=None,
        )
        db.add(anatomy_template)
        db.flush()

        anatomy_items = [
            ("Liver", "#8B4513"),
            ("Gallbladder", "#228B22"),
            ("Stomach", "#FFB6C1"),
            ("Intestine", "#DEB887"),
            ("Peritoneum", "#F0E68C"),
            ("Blood Vessel", "#DC143C"),
            ("Fat", "#FFFACD"),
            ("Connective Tissue", "#D3D3D3"),
        ]

        for i, (name, color) in enumerate(anatomy_items):
            item = models.TemplateCategoryItem(
                template_id=anatomy_template.id,
                name=name,
                color=color,
                order=i,
            )
            db.add(item)

        db.commit()
        logger.info("Successfully seeded 2 system category templates")

    except Exception as e:
        logger.error(f"Failed to seed system templates: {e}")
        db.rollback()
    finally:
        db.close()


# Seed templates on startup
seed_system_templates()

app = FastAPI(
    title="Medical Video Annotation API",
    description="FastAPI backend for medical video annotation tool with SAM integration",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors for debugging 422 responses"""
    logger.error(f"Validation error on {request.method} {request.url.path}")
    logger.error(f"Validation errors: {exc.errors()}")
    # Try to log body for debugging (may fail for large bodies)
    try:
        body = await request.body()
        body_preview = body[:500].decode("utf-8", errors="replace") if body else "empty"
        logger.error(f"Request body preview: {body_preview}")
    except Exception as e:
        logger.error(f"Could not read request body: {e}")

    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"message": "Internal server error"})


@app.get("/")
async def root():
    return {"message": "Medical Video Annotation API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


app.include_router(api_router, prefix=settings.API_V1_STR)
