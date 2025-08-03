from typing import List
from sqlalchemy.orm import Session

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

    def create_with_owner(
        self, db: Session, *, obj_in: ProjectCreate, owner_id: int
    ) -> Project:
        obj_in_data = obj_in.dict()
        
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
                'name': obj_in_data.get('name'),
                'description': obj_in_data.get('description')
            }
            db_obj = self.model(**basic_data, owner_id=owner_id)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


project = CRUDProject(Project)