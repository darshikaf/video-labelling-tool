import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.models import User
from app.schemas.schemas import UserCreate, UserBase


class CRUDUser(CRUDBase[User, UserCreate, UserBase]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            password_hash=get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(
        self, db: Session, *, email: str, password: str
    ) -> Optional[User]:
        logger = logging.getLogger(__name__)
        
        user = self.get_by_email(db, email=email)
        if not user:
            logger.warning(f"AUTH DEBUG: User not found for email: {email}")
            return None
        
        logger.info(f"AUTH DEBUG: User found: {user.email}, checking password...")
        password_valid = verify_password(password, user.password_hash)
        logger.info(f"AUTH DEBUG: Password valid: {password_valid}")
        
        if not password_valid:
            return None
        return user


user = CRUDUser(User)