from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # System-generated unique name
    display_name = Column(String, nullable=False)  # User-provided display name
    description = Column(Text, nullable=True)
    annotation_format = Column(String, nullable=False, default='YOLO')  # YOLO, COCO, PASCAL_VOC
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    videos = relationship("Video", back_populates="project", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="project", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    total_frames = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="videos")
    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")


class Frame(Base):
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    frame_number = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    video = relationship("Video", back_populates="frames")
    annotations = relationship("Annotation", back_populates="frame", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)  # Hex color code
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="categories")
    annotations = relationship("Annotation", back_populates="category")


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    frame_id = Column(Integer, ForeignKey("frames.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    mask_storage_key = Column(String, nullable=False)  # Object storage key for mask
    annotation_storage_key = Column(String, nullable=True)  # Object storage key for annotation file
    sam_points = Column(Text, nullable=True)  # JSON string of SAM prompt points
    sam_boxes = Column(Text, nullable=True)  # JSON string of SAM prompt boxes
    confidence = Column(Float, nullable=True)
    is_reviewed = Column(Boolean, default=False)
    # Additional metadata for model training
    mask_width = Column(Integer, nullable=True)  # Original mask dimensions
    mask_height = Column(Integer, nullable=True)
    polygon_points = Column(Text, nullable=True)  # JSON string of polygon vertices if available
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    frame = relationship("Frame", back_populates="annotations")
    category = relationship("Category", back_populates="annotations")