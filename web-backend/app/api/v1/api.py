from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, videos, annotations, sam, masks
from app.routers import export

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(annotations.router, prefix="/annotations", tags=["annotations"])
api_router.include_router(annotations.router, prefix="", tags=["annotations"])  # For video-based annotation routes
api_router.include_router(sam.router, prefix="/sam", tags=["sam"])
api_router.include_router(masks.router, prefix="/masks", tags=["masks"])
api_router.include_router(export.router, prefix="/export", tags=["export"])