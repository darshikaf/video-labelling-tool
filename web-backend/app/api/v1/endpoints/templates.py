from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db.database import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.CategoryTemplate])
def get_templates(
    db: Session = Depends(get_db),
    include_system: bool = True,
    user_id: int = None,
):
    """Get all category templates (system + user-created)"""
    query = db.query(models.CategoryTemplate)

    if not include_system and user_id:
        query = query.filter(models.CategoryTemplate.created_by == user_id)

    templates = query.all()
    return templates


@router.get("/{template_id}", response_model=schemas.CategoryTemplate)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific template by ID"""
    template = db.query(models.CategoryTemplate).filter(
        models.CategoryTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.post("/", response_model=schemas.CategoryTemplate)
def create_template(
    template_in: schemas.CategoryTemplateCreate,
    db: Session = Depends(get_db),
    user_id: int = 1,  # Default user for prototype
):
    """Create a new category template"""
    # Check for duplicate name
    existing = db.query(models.CategoryTemplate).filter(
        models.CategoryTemplate.name == template_in.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template with this name already exists")

    # Create template
    template = models.CategoryTemplate(
        name=template_in.name,
        description=template_in.description,
        is_system=False,
        created_by=user_id,
    )
    db.add(template)
    db.flush()

    # Create template items
    for i, item in enumerate(template_in.items):
        template_item = models.TemplateCategoryItem(
            template_id=template.id,
            name=item.name,
            color=item.color,
            order=item.order if item.order else i,
        )
        db.add(template_item)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """Delete a template (only user-created, not system templates)"""
    template = db.query(models.CategoryTemplate).filter(
        models.CategoryTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system templates")

    db.delete(template)
    db.commit()

    return {"message": f"Template '{template.name}' deleted successfully"}


@router.post("/{template_id}/apply/{project_id}")
def apply_template_to_project(
    template_id: int,
    project_id: int,
    request: schemas.ApplyTemplateRequest = None,
    db: Session = Depends(get_db),
):
    """Apply a template's categories to a project"""
    # Get template
    template = db.query(models.CategoryTemplate).filter(
        models.CategoryTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get project
    project = db.query(models.Project).filter(
        models.Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    merge = request.merge if request else False

    # If not merging, delete existing categories (that have no annotations)
    if not merge:
        existing_categories = db.query(models.Category).filter(
            models.Category.project_id == project_id
        ).all()

        categories_with_annotations = []
        for cat in existing_categories:
            annotation_count = db.query(models.Annotation).filter(
                models.Annotation.category_id == cat.id
            ).count()
            if annotation_count > 0:
                categories_with_annotations.append(cat.name)
            else:
                db.delete(cat)

        if categories_with_annotations:
            # Don't delete categories that have annotations, just warn
            pass

    # Add template categories to project
    added_count = 0
    skipped_count = 0

    for item in template.items:
        # Check if category already exists
        existing = db.query(models.Category).filter(
            models.Category.project_id == project_id,
            models.Category.name == item.name
        ).first()

        if existing:
            skipped_count += 1
            continue

        category = models.Category(
            project_id=project_id,
            name=item.name,
            color=item.color,
        )
        db.add(category)
        added_count += 1

    db.commit()

    return {
        "message": f"Template '{template.name}' applied to project",
        "categories_added": added_count,
        "categories_skipped": skipped_count,
    }
