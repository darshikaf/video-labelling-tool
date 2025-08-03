from typing import List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.models import Video
from app.schemas.schemas import VideoCreate, VideoBase


class CRUDVideo(CRUDBase[Video, VideoCreate, VideoBase]):
    def get_by_project(
        self, db: Session, *, project_id: int, skip: int = 0, limit: int = 100
    ) -> List[Video]:
        return (
            db.query(self.model)
            .filter(Video.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_project(
        self, db: Session, *, obj_in: VideoCreate, project_id: int, file_path: str
    ) -> Video:
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data, project_id=project_id, file_path=file_path)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


video = CRUDVideo(Video)