from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import crud, models, schemas
from app.api import deps
from app.db.database import get_db

router = APIRouter()


def get_or_create_frame(db: Session, video_id: int, frame_number: int):
    """Get or create a frame record"""
    # Check if frame already exists
    existing_frame = db.query(models.Frame).filter(
        models.Frame.video_id == video_id,
        models.Frame.frame_number == frame_number
    ).first()
    
    if existing_frame:
        return existing_frame
    
    # Create new frame record with default dimensions
    new_frame = models.Frame(
        video_id=video_id,
        frame_number=frame_number,
        width=640,  # Using our standard processing dimensions
        height=480
    )
    db.add(new_frame)
    db.commit()
    db.refresh(new_frame)
    return new_frame


def get_or_create_category(db: Session, project_id: int, name: str, color: str = None):
    """Get or create a category"""
    existing_category = db.query(models.Category).filter(
        models.Category.project_id == project_id,
        models.Category.name == name
    ).first()
    
    if existing_category:
        return existing_category
    
    # Create new category with random color if not provided
    if not color:
        import random
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
        color = random.choice(colors)
    
    new_category = models.Category(
        project_id=project_id,
        name=name,
        color=color
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


class AnnotationRequest(schemas.BaseModel):
    category_name: str
    mask_data: str
    sam_points: str = None
    sam_boxes: str = None
    confidence: float = None

@router.post("/videos/{video_id}/frames/{frame_number}/annotations")
def create_annotation_for_video_frame(
    video_id: int,
    frame_number: int,
    request: AnnotationRequest,
    db: Session = Depends(get_db),
):
    """Create annotation for a specific video frame"""
    import base64
    import gzip
    import json
    
    try:
        # Get video to find project_id
        video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get or create frame
        frame = get_or_create_frame(db, video_id, frame_number)
        
        # Get or create category
        category = get_or_create_category(db, video.project_id, request.category_name)
        
        # Decode base64 mask data and compress it for storage
        mask_bytes = base64.b64decode(request.mask_data)
        compressed_mask = gzip.compress(mask_bytes)
        
        # Create annotation
        annotation_data = schemas.AnnotationCreate(
            category_id=category.id,
            mask_data=request.mask_data,
            sam_points=request.sam_points,
            sam_boxes=request.sam_boxes,
            confidence=request.confidence
        )
        
        annotation = crud.annotation.create_with_frame(
            db=db, 
            obj_in=annotation_data, 
            frame_id=frame.id,
            mask_data=compressed_mask
        )
        
        return {
            "id": annotation.id,
            "frame_id": annotation.frame_id,
            "category": {"id": category.id, "name": category.name, "color": category.color},
            "created_at": annotation.created_at
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid annotation data: {str(e)}")


@router.get("/frames/{frame_id}/annotations", response_model=List[schemas.Annotation])
def read_frame_annotations(
    frame_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    # TODO: Add authorization check through video -> project -> owner
    annotations = crud.annotation.get_by_frame(
        db=db, frame_id=frame_id, skip=skip, limit=limit
    )
    return annotations


@router.post("/frames/{frame_id}/annotations", response_model=schemas.Annotation)
def create_annotation(
    frame_id: int,
    annotation_in: schemas.AnnotationCreate,
    db: Session = Depends(get_db),
):
    import base64
    import gzip
    
    try:
        # Decode base64 mask data and compress it for storage
        mask_bytes = base64.b64decode(annotation_in.mask_data)
        compressed_mask = gzip.compress(mask_bytes)
        
        # Create annotation with compressed mask data
        annotation = crud.annotation.create_with_frame(
            db=db, 
            obj_in=annotation_in, 
            frame_id=frame_id,
            mask_data=compressed_mask
        )
        return annotation
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mask data: {str(e)}")


@router.put("/{annotation_id}", response_model=schemas.Annotation)
def update_annotation(
    annotation_id: int,
    annotation_update: schemas.AnnotationBase,
    db: Session = Depends(get_db),
):
    annotation = crud.annotation.get(db=db, id=annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    # TODO: Add authorization check
    annotation = crud.annotation.update(
        db=db, db_obj=annotation, obj_in=annotation_update
    )
    return annotation


@router.delete("/{annotation_id}")
def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    annotation = crud.annotation.get(db=db, id=annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    # TODO: Add authorization check
    crud.annotation.remove(db=db, id=annotation_id)
    return {"message": "Annotation deleted successfully"}