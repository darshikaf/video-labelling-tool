from typing import List
from sqlalchemy.orm import Session
from datetime import datetime
import re

from app.crud.base import CRUDBase
from app.models.models import Project
from app.schemas.schemas import ProjectCreate, ProjectBase


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectBase]):
    def get_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            db.query(self.model)
            .filter(Project.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def _sanitize_project_name(self, name: str) -> str:
        """Sanitize user input for project name"""
        # Convert to lowercase, replace spaces and special chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Limit length to 50 characters
        return sanitized[:50]
    
    def _generate_standard_name(self, user_name: str, annotation_format: str) -> str:
        """Generate standardized project name"""
        sanitized_name = self._sanitize_project_name(user_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        format_suffix = annotation_format.upper()
        
        return f"{sanitized_name}_{timestamp}_{format_suffix}"
    
    def _is_name_unique(self, db: Session, name: str, owner_id: int) -> bool:
        """Check if project name is unique for the owner"""
        existing = db.query(self.model).filter(
            Project.name == name,
            Project.owner_id == owner_id
        ).first()
        return existing is None
    
    def get_by_name_and_owner(self, db: Session, *, name: str, owner_id: int):
        """Get project by name and owner"""
        return db.query(self.model).filter(
            Project.name == name,
            Project.owner_id == owner_id
        ).first()

    def create_with_owner(
        self, db: Session, *, obj_in: ProjectCreate, owner_id: int
    ) -> Project:
        obj_in_data = obj_in.dict()
        
        # Store original user input as display_name
        display_name = obj_in_data.get('name', 'project')
        annotation_format = obj_in_data.get('annotation_format', 'YOLO')
        
        # Generate standardized unique system name
        standard_name = self._generate_standard_name(display_name, annotation_format)
        
        # Ensure uniqueness (in case of rapid concurrent requests)
        counter = 1
        final_name = standard_name
        while not self._is_name_unique(db, final_name, owner_id):
            final_name = f"{standard_name}_{counter:02d}"
            counter += 1
            if counter > 99:  # Safety limit
                raise ValueError("Unable to generate unique project name")
        
        # Update the data with system name and preserve display name
        obj_in_data['name'] = final_name
        obj_in_data['display_name'] = display_name
        
        # Filter out fields that don't exist in the database model yet
        # This provides backward compatibility during migration
        try:
            from sqlalchemy import inspect
            mapper = inspect(self.model)
            valid_columns = [column.key for column in mapper.columns]
            
            # Only include fields that exist in the database model
            filtered_data = {k: v for k, v in obj_in_data.items() 
                           if k in valid_columns}
            
            db_obj = self.model(**filtered_data, owner_id=owner_id)
        except Exception as e:
            # Fallback: try with basic fields only
            print(f"Column filtering failed, using basic fields: {e}")
            basic_data = {
                'name': final_name,
                'display_name': display_name,
                'description': obj_in_data.get('description')
            }
            db_obj = self.model(**basic_data, owner_id=owner_id)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


project = CRUDProject(Project)