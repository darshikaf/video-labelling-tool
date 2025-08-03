from typing import List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.models import Annotation
from app.schemas.schemas import AnnotationCreate, AnnotationBase


class CRUDAnnotation(CRUDBase[Annotation, AnnotationCreate, AnnotationBase]):
    def get_by_frame(
        self, db: Session, *, frame_id: int, skip: int = 0, limit: int = 100
    ) -> List[Annotation]:
        return (
            db.query(self.model)
            .filter(Annotation.frame_id == frame_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_frame(
        self, db: Session, *, obj_in: AnnotationCreate, frame_id: int, mask_data: bytes
    ) -> Annotation:
        obj_in_data = obj_in.dict()
        # Remove mask_data from obj_in_data since we're passing it separately
        obj_in_data.pop('mask_data', None)
        db_obj = self.model(**obj_in_data, frame_id=frame_id, mask_data=mask_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


annotation = CRUDAnnotation(Annotation)