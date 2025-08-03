import os
import shutil
from pathlib import Path
from typing import List
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.db.database import get_db

router = APIRouter()


def process_video_metadata(file_path: str) -> dict:
    """Extract metadata from video file using OpenCV"""
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else None
        
        cap.release()
        
        return {
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'duration': duration
        }
    except Exception as e:
        print(f"Error processing video metadata: {e}")
        return {}


@router.get("/", response_model=List[schemas.Project])
def read_projects(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    owner_id: int = 1,  # Default user for prototype
):
    projects = crud.project.get_by_owner(
        db=db, owner_id=owner_id, skip=skip, limit=limit
    )
    return projects


@router.post("/", response_model=schemas.Project)
def create_project(
    project_in: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    owner_id: int = 1,  # Default user for prototype
):
    project = crud.project.create_with_owner(
        db=db, obj_in=project_in, owner_id=owner_id
    )
    return project


@router.get("/{project_id}", response_model=schemas.Project)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/videos", response_model=List[schemas.Video])
def read_project_videos(
    project_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    videos = crud.video.get_by_project(
        db=db, project_id=project_id, skip=skip, limit=limit
    )
    return videos


@router.post("/{project_id}/videos", response_model=schemas.Video)
async def upload_video(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Verify project exists
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file type
    allowed_extensions = {'.mp4', '.avi', '.mov', '.qt', '.mkv', '.wmv'}
    file_extension = Path(file.filename or "").suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Create upload directory
    upload_dir = Path(settings.UPLOAD_DIR) / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_path = upload_dir / file.filename
    counter = 1
    while file_path.exists():
        name = Path(file.filename).stem
        ext = Path(file.filename).suffix
        file_path = upload_dir / f"{name}_{counter}{ext}"
        counter += 1
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        # Process video metadata
        metadata = process_video_metadata(str(file_path))
        
        # Create video record
        video_create = schemas.VideoCreate(
            filename=file_path.name,
            file_size=file_size,
            **metadata
        )
        
        video = crud.video.create_with_project(
            db=db, 
            obj_in=video_create, 
            project_id=project_id, 
            file_path=str(file_path)
        )
        
        return video
        
    except Exception as e:
        # Clean up file if database operation fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")