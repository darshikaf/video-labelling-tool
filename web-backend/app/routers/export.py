# web-backend/app/routers/export.py
"""
Export API endpoints - following Streamlit prototype patterns
"""

import logging
import os
import tempfile
import zipfile
from typing import List, Optional

from app.services.export_service import export_service
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats"""
    try:
        formats = export_service.get_supported_formats()
        return {
            "success": True,
            "formats": formats,
            "message": f"Found {len(formats)} supported formats",
        }
    except Exception as e:
        logger.error(f"Failed to get supported formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/project/{project_id}")
async def export_project(
    project_id: int,
    format: str = Query(..., description="Export format (COCO, YOLO, etc.)"),
    video_id: Optional[int] = Query(
        None, description="Optional: export only specific video"
    ),
    background_tasks: BackgroundTasks = None,
):
    """
    Export annotations for a project in specified format
    Following Streamlit prototype patterns
    """
    try:
        logger.info(
            f"Starting export: project_id={project_id}, format={format}, video_id={video_id}"
        )

        # Validate format
        supported_formats = export_service.get_supported_formats()
        if format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{format}'. Supported: {supported_formats}",
            )

        # Perform export
        exported_path = export_service.export_project_annotations(
            project_id=project_id, export_format=format, video_id=video_id
        )

        # Return download info
        # Note: download_url should NOT include /api/v1 prefix since frontend adds it
        return {
            "success": True,
            "exported_path": exported_path,
            "format": format,
            "project_id": project_id,
            "video_id": video_id,
            "download_url": f"/export/download?path={os.path.basename(exported_path)}",
        }

    except ValueError as e:
        logger.error(f"Export validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/download")
async def download_export(path: str = Query(..., description="Export file path")):
    """Download exported file or directory (zipped)"""
    try:
        # Security: only allow files from exports directory
        exports_dir = "exports"
        full_path = os.path.join(exports_dir, path)

        # Validate path exists and is within exports directory
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=404, detail=f"Export file not found: {path}"
            )

        # Resolve any potential path traversal issues
        full_path = os.path.abspath(full_path)
        exports_dir = os.path.abspath(exports_dir)
        if not full_path.startswith(exports_dir):
            raise HTTPException(status_code=403, detail="Invalid file path")

        if os.path.isfile(full_path):
            # Single file download
            return FileResponse(
                path=full_path,
                filename=os.path.basename(full_path),
                media_type="application/octet-stream",
            )
        else:
            # Directory - zip it first
            logger.info(f"Creating zip archive for directory: {full_path}")
            zip_filename = f"{os.path.basename(full_path)}.zip"
            zip_path = os.path.join(exports_dir, zip_filename)

            # Create zip file
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, full_path)
                        zipf.write(file_path, arcname)

            logger.info(f"Created zip archive: {zip_path}")

            return FileResponse(
                path=zip_path, filename=zip_filename, media_type="application/zip"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/status/{project_id}")
async def get_export_status(project_id: int):
    """Get export status for a project (for future async export support)"""
    # For now, just return basic project info
    # This can be extended for background export tasks
    return {
        "success": True,
        "project_id": project_id,
        "status": "ready",
        "message": "Project ready for export",
    }


@router.get("/debug/{project_id}")
async def debug_export_data(
    project_id: int,
    video_id: Optional[int] = Query(None, description="Optional video ID filter"),
):
    """Debug endpoint to check what data is available for export"""
    from app.db.database import SessionLocal
    from app.models.models import Annotation, Category, Frame, Project, Video

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": f"Project {project_id} not found"}

        categories = db.query(Category).filter(Category.project_id == project_id).all()

        video_query = db.query(Video).filter(Video.project_id == project_id)
        if video_id:
            video_query = video_query.filter(Video.id == video_id)
        videos = video_query.all()

        result = {
            "project": {"id": project.id, "name": project.name},
            "categories": [{"id": c.id, "name": c.name} for c in categories],
            "videos": [],
        }

        for video in videos:
            frames = db.query(Frame).filter(Frame.video_id == video.id).all()
            video_data = {
                "id": video.id,
                "filename": video.filename,
                "frames_count": len(frames),
                "frames_with_annotations": 0,
                "total_annotations": 0,
                "sample_annotations": [],
            }

            for frame in frames:
                annotations = (
                    db.query(Annotation).filter(Annotation.frame_id == frame.id).all()
                )
                if annotations:
                    video_data["frames_with_annotations"] += 1
                    video_data["total_annotations"] += len(annotations)

                    # Include first few annotations as samples
                    if len(video_data["sample_annotations"]) < 3:
                        for anno in annotations[:2]:
                            video_data["sample_annotations"].append(
                                {
                                    "id": anno.id,
                                    "frame_id": anno.frame_id,
                                    "frame_number": frame.frame_number,
                                    "category_id": anno.category_id,
                                    "mask_storage_key": anno.mask_storage_key,
                                    "has_mask_key": bool(anno.mask_storage_key),
                                }
                            )

            result["videos"].append(video_data)

        return result
    finally:
        db.close()
