from typing import Optional, List
from pydantic import BaseModel, validator
from datetime import datetime


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    categories: Optional[List[str]] = None


class Project(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class CategoryBase(BaseModel):
    name: str
    color: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    project_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class VideoBase(BaseModel):
    filename: str


class VideoCreate(VideoBase):
    file_size: int
    duration: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    total_frames: Optional[int] = None


class Video(VideoBase):
    id: int
    project_id: int
    file_path: str
    file_size: int
    duration: Optional[float]
    fps: Optional[float]
    width: Optional[int]
    height: Optional[int]
    total_frames: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class FrameBase(BaseModel):
    frame_number: int
    width: int
    height: int


class FrameCreate(FrameBase):
    pass


class Frame(FrameBase):
    id: int
    video_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class AnnotationBase(BaseModel):
    sam_points: Optional[str] = None
    sam_boxes: Optional[str] = None
    confidence: Optional[float] = None
    mask_width: Optional[int] = None
    mask_height: Optional[int] = None
    polygon_points: Optional[str] = None


class AnnotationCreate(AnnotationBase):
    category_id: int
    mask_data: str  # Base64 encoded mask data (will be stored in object storage)


class Annotation(AnnotationBase):
    id: int
    frame_id: int
    category_id: int
    mask_storage_key: str  # Object storage key for mask
    is_reviewed: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None