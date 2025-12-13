import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.db.database import get_db
from app.services.annotation_formats import annotation_format_service
from app.services.storage_service import storage_service

router = APIRouter()


def get_or_create_frame(db: Session, video_id: int, frame_number: int):
    """Get or create a frame record"""
    # Check if frame already exists
    existing_frame = (
        db.query(models.Frame)
        .filter(
            models.Frame.video_id == video_id, models.Frame.frame_number == frame_number
        )
        .first()
    )

    if existing_frame:
        return existing_frame

    # Create new frame record with default dimensions
    new_frame = models.Frame(
        video_id=video_id,
        frame_number=frame_number,
        width=640,  # Using our standard processing dimensions
        height=480,
    )
    db.add(new_frame)
    db.commit()
    db.refresh(new_frame)
    return new_frame


def get_or_create_category(db: Session, project_id: int, name: str, color: str = None):
    """Get or create a category"""
    existing_category = (
        db.query(models.Category)
        .filter(models.Category.project_id == project_id, models.Category.name == name)
        .first()
    )

    if existing_category:
        return existing_category

    # Create new category with random color if not provided
    if not color:
        import random

        colors = [
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#96CEB4",
            "#FFEAA7",
            "#DDA0DD",
            "#98D8C8",
            "#F7DC6F",
        ]
        color = random.choice(colors)

    new_category = models.Category(project_id=project_id, name=name, color=color)
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
    import io

    try:
        # Get video to find project_id
        video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Get project to access annotation format
        project = (
            db.query(models.Project)
            .filter(models.Project.id == video.project_id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get or create frame
        frame = get_or_create_frame(db, video_id, frame_number)

        # Get or create category
        category = get_or_create_category(db, video.project_id, request.category_name)

        # Get mask dimensions for metadata
        mask_width, mask_height = 640, 480  # Default SAM dimensions
        try:
            # Try to decode mask data to get actual dimensions
            mask_data = request.mask_data
            if mask_data.startswith("data:image"):
                mask_data = mask_data.split(",")[1]
            mask_bytes = base64.b64decode(mask_data)

            # Get image dimensions
            with Image.open(io.BytesIO(mask_bytes)) as img:
                mask_width, mask_height = img.size
        except Exception:
            # Use defaults if unable to determine dimensions
            pass

        # Create annotation record first to get ID
        annotation_data = {
            "frame_id": frame.id,
            "category_id": category.id,
            "sam_points": request.sam_points,
            "sam_boxes": request.sam_boxes,
            "confidence": request.confidence,
            "mask_width": mask_width,
            "mask_height": mask_height,
            "mask_storage_key": "",  # Temporary, will be updated after storing
        }

        # Only add annotation_storage_key if the field exists in the model
        # This handles cases where database migration hasn't been run yet
        try:
            # Check if the model has the annotation_storage_key field
            from sqlalchemy import inspect

            mapper = inspect(models.Annotation)
            if "annotation_storage_key" in [column.key for column in mapper.columns]:
                annotation_data["annotation_storage_key"] = ""
        except Exception:
            # If inspection fails, try to create without the field
            pass

        annotation = models.Annotation(**annotation_data)
        db.add(annotation)
        db.flush()  # Get the ID without committing

        # Generate annotation in project's preferred format (with fallback)
        try:
            annotation_format = getattr(project, "annotation_format", "YOLO") or "YOLO"
        except AttributeError:
            # annotation_format field doesn't exist yet, use default
            annotation_format = "YOLO"

        # Prepare annotation data for format conversion
        format_data = {
            "category_id": category.id,
            "category_name": category.name,
            "mask_data": request.mask_data,
            "sam_points": request.sam_points,
            "sam_boxes": request.sam_boxes,
            "confidence": request.confidence,
            "mask_width": mask_width,
            "mask_height": mask_height,
        }

        # Set format service dimensions based on actual mask
        annotation_format_service.image_width = mask_width
        annotation_format_service.image_height = mask_height

        # Convert to annotation format
        try:
            # Pass format-specific parameters
            if annotation_format.upper() == "COCO":
                annotation_content = annotation_format_service.convert_annotation(
                    format_data, annotation_format, image_id=frame.id
                )
            elif annotation_format.upper() == "PASCAL_VOC":
                # Pascal VOC needs image filename
                image_filename = f"frame_{frame_number}.jpg"
                annotation_content = annotation_format_service.convert_annotation(
                    format_data, annotation_format, image_filename=image_filename
                )
            else:
                # YOLO and other formats don't need extra parameters
                annotation_content = annotation_format_service.convert_annotation(
                    format_data, annotation_format
                )

            if not annotation_content.strip():
                print(
                    f"Warning: Empty annotation content generated for format {annotation_format}"
                )
                annotation_content = (
                    f"# No annotation data generated for {annotation_format} format"
                )

        except Exception as format_error:
            print(
                f"Error generating annotation format {annotation_format}: {format_error}"
            )
            # Fallback annotation content
            annotation_content = (
                f"# Error generating {annotation_format} format: {str(format_error)}"
            )

        # For now, just store the mask (fallback for when annotation storage isn't available)
        try:
            # Try to store both mask and annotation files
            storage_keys = storage_service.store_mask_and_annotation(
                project_id=video.project_id,
                video_id=video_id,
                frame_number=frame_number,
                annotation_id=annotation.id,
                mask_data=request.mask_data,
                annotation_content=annotation_content,
                format_type=annotation_format,
            )

            # Update annotation with storage keys
            annotation.mask_storage_key = storage_keys["mask_storage_key"]

            # Only set annotation_storage_key if the field exists
            if hasattr(annotation, "annotation_storage_key"):
                annotation.annotation_storage_key = storage_keys[
                    "annotation_storage_key"
                ]

        except Exception as storage_error:
            print(f"Dual storage failed, falling back to mask only: {storage_error}")
            # Fallback to just storing the mask
            mask_key = storage_service.store_mask(
                project_id=video.project_id,
                video_id=video_id,
                frame_number=frame_number,
                annotation_id=annotation.id,
                mask_data=request.mask_data,
            )
            annotation.mask_storage_key = mask_key

        db.commit()
        db.refresh(annotation)

        # Build response with conditional fields
        response = {
            "id": annotation.id,
            "frame_id": annotation.frame_id,
            "category": {
                "id": category.id,
                "name": category.name,
                "color": category.color,
            },
            "mask_storage_key": annotation.mask_storage_key,
            "annotation_format": annotation_format,
            "created_at": annotation.created_at,
        }

        # Only include annotation_storage_key if it exists
        if (
            hasattr(annotation, "annotation_storage_key")
            and annotation.annotation_storage_key
        ):
            response["annotation_storage_key"] = annotation.annotation_storage_key

        return response

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to create annotation: {str(e)}"
        )


@router.get("/videos/{video_id}/frames/{frame_number}/annotations")
def get_annotations_for_video_frame(
    video_id: int,
    frame_number: int,
    db: Session = Depends(get_db),
):
    """Get all annotations for a specific video frame"""
    # Find the frame by video_id and frame_number
    frame = (
        db.query(models.Frame)
        .filter(
            models.Frame.video_id == video_id, models.Frame.frame_number == frame_number
        )
        .first()
    )

    if not frame:
        # No frame record = no annotations yet
        return []

    # Get all annotations for this frame
    annotations = crud.annotation.get_by_frame(db=db, frame_id=frame.id)

    # Return annotations with mask data
    result = []
    for ann in annotations:
        ann_dict = {
            "id": ann.id,
            "frame_id": ann.frame_id,
            "category_id": ann.category_id,
            "mask_storage_key": ann.mask_storage_key,
            "sam_points": ann.sam_points,
            "sam_boxes": ann.sam_boxes,
            "confidence": ann.confidence,
            "created_at": ann.created_at,
            "updated_at": ann.updated_at,
        }

        # Include category info if available
        if ann.category:
            ann_dict["category_name"] = ann.category.name
            ann_dict["category_color"] = ann.category.color

        # Provide API endpoint for mask retrieval (avoids MinIO hostname issues)
        if ann.mask_storage_key:
            ann_dict["mask_url"] = f"/api/v1/annotations/{ann.id}/mask"

        result.append(ann_dict)

    return result


@router.get("/annotations/{annotation_id}/mask")
def get_annotation_mask_data(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    """Get the actual mask image data for an annotation"""
    import base64

    from fastapi.responses import Response

    annotation = crud.annotation.get(db=db, id=annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if not annotation.mask_storage_key:
        raise HTTPException(
            status_code=404, detail="No mask data found for this annotation"
        )

    try:
        # Get the mask data from MinIO
        mask_bytes = storage_service.get_mask_data(annotation.mask_storage_key)

        # Return as PNG image
        return Response(content=mask_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve mask: {str(e)}"
        )


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


@router.get("/{annotation_id}/mask-url")
def get_annotation_mask_url(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    """Get presigned URL for annotation mask"""
    annotation = crud.annotation.get(db=db, id=annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    try:
        mask_url = storage_service.get_mask_url(annotation.mask_storage_key)
        return {"mask_url": mask_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate mask URL: {str(e)}"
        )


@router.get("/{annotation_id}/annotation-url")
def get_annotation_file_url(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    """Get presigned URL for annotation file (YOLO, COCO, Pascal VOC)"""
    annotation = crud.annotation.get(db=db, id=annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if not annotation.annotation_storage_key:
        raise HTTPException(status_code=404, detail="Annotation file not found")

    try:
        annotation_url = storage_service.get_annotation_url(
            annotation.annotation_storage_key
        )
        return {"annotation_url": annotation_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate annotation URL: {str(e)}"
        )


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
            db=db, obj_in=annotation_in, frame_id=frame_id, mask_data=compressed_mask
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
