import os
import shutil
from pathlib import Path
from typing import List
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
        import cv2  # Import cv2 only when needed
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
    except ImportError:
        print("OpenCV not available - using default metadata")
        return {'fps': 30, 'total_frames': 100, 'width': 640, 'height': 480, 'duration': 3.33}
    except Exception as e:
        print(f"Error processing video metadata: {e}")
        return {'fps': 30, 'total_frames': 100, 'width': 640, 'height': 480, 'duration': 3.33}


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
    try:
        # Extract categories before creating project (since it's not a Project model field)
        categories = project_in.categories
        
        # Create a clean project object without categories field
        project_data = schemas.ProjectBase(
            name=project_in.name,
            description=project_in.description
        )
        
        # Create project
        project = crud.project.create_with_owner(
            db=db, obj_in=project_data, owner_id=owner_id
        )
        
        # Create categories if provided
        if categories:
            import random
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
            
            for category_name in categories:
                color = random.choice(colors)
                category = models.Category(
                    project_id=project.id,
                    name=category_name,
                    color=color
                )
                db.add(category)
            
            # Commit the categories
            db.commit()
        
        return project
        
    except Exception as e:
        db.rollback()
        print(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/{project_id}/categories")
def get_project_categories(
    project_id: int,
    db: Session = Depends(get_db),
):
    """Get all categories for a project"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    categories = db.query(models.Category).filter(models.Category.project_id == project_id).all()
    return [{"id": cat.id, "name": cat.name, "color": cat.color} for cat in categories]


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