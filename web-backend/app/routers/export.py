# web-backend/app/routers/export.py
"""
Export API endpoints - following Streamlit prototype patterns
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional, List
import os
import logging

from app.services.export_service import export_service

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
            "message": f"Found {len(formats)} supported formats"
        }
    except Exception as e:
        logger.error(f"Failed to get supported formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/project/{project_id}")
async def export_project(
    project_id: int,
    format: str = Query(..., description="Export format (COCO, YOLO, etc.)"),
    video_id: Optional[int] = Query(None, description="Optional: export only specific video"),
    background_tasks: BackgroundTasks = None
):
    """
    Export annotations for a project in specified format
    Following Streamlit prototype patterns
    """
    try:
        logger.info(f"Starting export: project_id={project_id}, format={format}, video_id={video_id}")
        
        # Validate format
        supported_formats = export_service.get_supported_formats()
        if format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{format}'. Supported: {supported_formats}"
            )
        
        # Perform export
        exported_path = export_service.export_project_annotations(
            project_id=project_id,
            export_format=format,
            video_id=video_id
        )
        
        # Return download info
        return {
            "success": True,
            "exported_path": exported_path,
            "format": format,
            "project_id": project_id,
            "video_id": video_id,
            "download_url": f"/api/export/download?path={os.path.basename(exported_path)}"
        }
        
    except ValueError as e:
        logger.error(f"Export validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/download")
async def download_export(path: str = Query(..., description="Export file path")):
    """Download exported file"""
    try:
        # Security: only allow files from exports directory
        exports_dir = "exports"
        full_path = os.path.join(exports_dir, path)
        
        # Validate path exists and is within exports directory
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
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
                media_type='application/octet-stream'
            )
        else:
            # Directory - would need to zip it first
            raise HTTPException(
                status_code=400, 
                detail="Directory downloads not implemented yet. Please export individual formats."
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
        "message": "Project ready for export"
    }