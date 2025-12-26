# web-backend/app/services/export_service.py
"""
Export service for annotation data - extensible format support
Based on Streamlit prototype patterns
"""

import base64
import datetime
import gzip
import io
import json
import logging
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from app.db.database import SessionLocal
from app.models.models import Annotation, Category, Frame, Project, Video
from app.services.storage_service import storage_service
from PIL import Image

logger = logging.getLogger(__name__)


class ExportFormatter(ABC):
    """Abstract base class for export formatters"""

    @abstractmethod
    def get_format_name(self) -> str:
        """Get the format name (e.g., 'COCO', 'YOLO')"""
        pass

    @abstractmethod
    def export(self, export_data: Dict[str, Any], output_path: str) -> str:
        """Export annotations in this format

        Args:
            export_data: Standardized annotation data
            output_path: Base path for export files

        Returns:
            Path to exported file/directory
        """
        pass


class COCOFormatter(ExportFormatter):
    """COCO format exporter - following Streamlit prototype patterns"""

    def get_format_name(self) -> str:
        return "COCO"

    def export(self, export_data: Dict[str, Any], output_path: str) -> str:
        """Export in COCO format following Streamlit implementation"""
        output_file = f"{output_path}_coco.json"

        # Create COCO format structure (same as Streamlit)
        coco_data = {
            "info": {
                "description": "SAM Video Segmentation Annotations",
                "date_created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
            },
            "images": [],
            "annotations": [],
            "categories": [],
        }

        # Add categories (following Streamlit pattern)
        category_mapping = {}
        for i, category in enumerate(export_data.get("categories", [])):
            category_id = i + 1
            category_mapping[category["name"]] = category_id
            coco_data["categories"].append(
                {"id": category_id, "name": category["name"], "supercategory": "object"}
            )

        # Add images and annotations
        annotation_id = 1
        for frame_data in export_data.get("frames", []):
            # Add image info
            image_id = frame_data["frame_number"] + 1
            coco_data["images"].append(
                {
                    "id": image_id,
                    "file_name": f"frame_{frame_data['frame_number']:06d}.jpg",
                    "width": frame_data["width"],
                    "height": frame_data["height"],
                }
            )

            # Process annotations for this frame
            for anno in frame_data.get("annotations", []):
                mask = self._decode_mask_from_png(anno.get("mask_bytes"))
                if mask is not None:
                    # Convert mask to contours (same as Streamlit)
                    contours, _ = cv2.findContours(
                        (mask > 0).astype(np.uint8),
                        cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE,
                    )

                    segmentation = []
                    for contour in contours:
                        contour = contour.flatten().tolist()
                        if len(contour) > 4:  # Valid polygons have at least 3 points
                            segmentation.append(contour)

                    if segmentation:
                        # Calculate bounding box
                        x, y, w, h = cv2.boundingRect((mask > 0).astype(np.uint8))

                        coco_data["annotations"].append(
                            {
                                "id": annotation_id,
                                "image_id": image_id,
                                "category_id": category_mapping.get(
                                    anno["category_name"], 1
                                ),
                                "segmentation": segmentation,
                                "area": float(np.sum(mask)),
                                "bbox": [x, y, w, h],
                                "iscrowd": 0,
                            }
                        )
                        annotation_id += 1

        # Save to file
        with open(output_file, "w") as f:
            json.dump(coco_data, f, indent=2)

        logger.info(f"Exported COCO format to: {output_file}")
        return output_file

    def _decode_mask_from_png(
        self, mask_bytes: Optional[bytes]
    ) -> Optional[np.ndarray]:
        """Decode mask from PNG bytes (from MinIO storage)"""
        if mask_bytes is None:
            return None
        try:
            # Load PNG image from bytes
            img = Image.open(io.BytesIO(mask_bytes))
            mask = np.array(img)

            # Convert to grayscale if needed
            if len(mask.shape) == 3:
                # If RGBA or RGB, take first channel or convert
                if mask.shape[2] == 4:
                    # RGBA - use alpha channel or first channel
                    mask = mask[:, :, 3] if mask[:, :, 3].max() > 0 else mask[:, :, 0]
                else:
                    # RGB - convert to grayscale
                    mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)

            return mask
        except Exception as e:
            logger.error(f"Failed to decode mask from PNG: {e}")
            return None


class YOLOFormatter(ExportFormatter):
    """YOLO format exporter - following Streamlit prototype patterns"""

    def get_format_name(self) -> str:
        return "YOLO"

    def export(self, export_data: Dict[str, Any], output_path: str) -> str:
        """Export in YOLO format following Streamlit implementation"""
        # Create directory for YOLO format (images + labels)
        yolo_dir = f"{output_path}_yolo"
        os.makedirs(os.path.join(yolo_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(yolo_dir, "labels"), exist_ok=True)

        # Create classes.txt (same as Streamlit)
        classes_file = os.path.join(yolo_dir, "classes.txt")
        with open(classes_file, "w") as f:
            for category in export_data.get("categories", []):
                f.write(f"{category['name']}\n")

        # Create class name to index mapping
        class_mapping = {
            cat["name"]: i for i, cat in enumerate(export_data.get("categories", []))
        }

        # For each frame with annotations, create a label file
        logger.info(
            f"YOLO Export: Processing {len(export_data.get('frames', []))} frames"
        )

        for frame_data in export_data.get("frames", []):
            if frame_data.get("annotations"):
                # Create label file
                label_file = os.path.join(
                    yolo_dir, "labels", f"frame_{frame_data['frame_number']:06d}.txt"
                )

                logger.info(
                    f"YOLO Export: Frame {frame_data['frame_number']} has {len(frame_data['annotations'])} annotations"
                )

                with open(label_file, "w") as f:
                    for anno in frame_data["annotations"]:
                        # Get class index
                        class_idx = class_mapping.get(anno["category_name"], 0)

                        # Debug: check if mask_bytes exists
                        mask_bytes = anno.get("mask_bytes")
                        logger.info(
                            f"YOLO Export: Annotation {anno['id']}, category={anno['category_name']}, mask_bytes={'present' if mask_bytes else 'MISSING'}, bytes_len={len(mask_bytes) if mask_bytes else 0}"
                        )

                        # Handle segmentation masks (load from PNG bytes)
                        mask = self._decode_mask_from_png(mask_bytes)
                        if mask is None:
                            logger.warning(
                                f"YOLO Export: Failed to decode mask for annotation {anno['id']}"
                            )
                            continue

                        logger.info(
                            f"YOLO Export: Mask decoded, shape={mask.shape}, max={mask.max()}, min={mask.min()}"
                        )

                        # For segmentation: convert to polygon format
                        contours, _ = cv2.findContours(
                            (mask > 0).astype(np.uint8),
                            cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE,
                        )

                        logger.info(
                            f"YOLO Export: Found {len(contours)} contours in mask"
                        )

                        # Format for YOLO segmentation annotation (polygon format)
                        for contour in contours:
                            img_w = frame_data["width"]
                            img_h = frame_data["height"]

                            # Normalize points
                            points = []
                            for pt in contour:
                                x, y = pt[0]
                                norm_x = x / img_w
                                norm_y = y / img_h
                                points.extend([norm_x, norm_y])

                            if len(points) > 5:  # At least 3 points (6 values)
                                points_str = " ".join([f"{p:.6f}" for p in points])
                                f.write(f"{class_idx} {points_str}\n")
                                logger.info(
                                    f"YOLO Export: Wrote polygon with {len(points) // 2} points"
                                )
                            else:
                                logger.warning(
                                    f"YOLO Export: Skipped contour with only {len(points) // 2} points"
                                )

        logger.info(f"Exported YOLO format to: {yolo_dir}")
        return yolo_dir

    def _decode_mask_from_png(
        self, mask_bytes: Optional[bytes]
    ) -> Optional[np.ndarray]:
        """Decode mask from PNG bytes (from MinIO storage)"""
        if mask_bytes is None:
            return None
        try:
            # Load PNG image from bytes
            img = Image.open(io.BytesIO(mask_bytes))
            mask = np.array(img)

            # Convert to grayscale if needed
            if len(mask.shape) == 3:
                # If RGBA or RGB, take first channel or convert
                if mask.shape[2] == 4:
                    # RGBA - use alpha channel or first channel
                    mask = mask[:, :, 3] if mask[:, :, 3].max() > 0 else mask[:, :, 0]
                else:
                    # RGB - convert to grayscale
                    mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)

            return mask
        except Exception as e:
            logger.error(f"Failed to decode mask from PNG: {e}")
            return None


class ExportService:
    """
    Main export service - extensible for multiple formats
    Based on Streamlit prototype architecture
    """

    def __init__(self):
        """Initialize export service with available formatters"""
        self.formatters: Dict[str, ExportFormatter] = {}
        self._register_default_formatters()

    def _register_default_formatters(self):
        """Register built-in formatters"""
        self.register_formatter(COCOFormatter())
        self.register_formatter(YOLOFormatter())

    def register_formatter(self, formatter: ExportFormatter):
        """Register a new export formatter"""
        self.formatters[formatter.get_format_name()] = formatter
        logger.info(f"Registered export formatter: {formatter.get_format_name()}")

    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return list(self.formatters.keys())

    def export_project_annotations(
        self, project_id: int, export_format: str, video_id: Optional[int] = None
    ) -> str:
        """
        Export annotations for a project or specific video

        Args:
            project_id: Project ID to export
            export_format: Format to export ('COCO', 'YOLO', etc.)
            video_id: Optional - export only specific video

        Returns:
            Path to exported file/directory
        """
        if export_format not in self.formatters:
            raise ValueError(f"Unsupported export format: {export_format}")

        # Get annotation data from database
        export_data = self._prepare_export_data(project_id, video_id)

        # Generate output path
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = export_data["project_name"].replace(" ", "_")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, f"{project_name}_{timestamp}")

            # Export using selected formatter
            formatter = self.formatters[export_format]
            exported_path = formatter.export(export_data, output_path)

            # Move to final location (you may want to configure this)
            final_dir = os.path.join("exports", f"{project_name}_{timestamp}")
            os.makedirs("exports", exist_ok=True)

            if os.path.isfile(exported_path):
                # Single file export
                final_path = os.path.join("exports", os.path.basename(exported_path))
                shutil.move(exported_path, final_path)
            else:
                # Directory export
                shutil.move(exported_path, final_dir)
                final_path = final_dir

            return final_path

    def _prepare_export_data(
        self, project_id: int, video_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Prepare standardized export data from database"""
        db = SessionLocal()
        try:
            # Get project info
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Get categories
            categories = (
                db.query(Category).filter(Category.project_id == project_id).all()
            )

            # Get videos (filtered by video_id if provided)
            video_query = db.query(Video).filter(Video.project_id == project_id)
            if video_id:
                video_query = video_query.filter(Video.id == video_id)
            videos = video_query.all()

            # Prepare export data structure
            export_data = {
                "project_name": project.name,
                "categories": [
                    {"id": cat.id, "name": cat.name, "color": cat.color}
                    for cat in categories
                ],
                "frames": [],
            }

            # Get frame and annotation data
            logger.info(f"Export: Found {len(videos)} videos for project {project_id}")

            for video in videos:
                frames = db.query(Frame).filter(Frame.video_id == video.id).all()
                logger.info(
                    f"Export: Video {video.id} ({video.filename}) has {len(frames)} frames in database"
                )

                for frame in frames:
                    annotations = (
                        db.query(Annotation)
                        .filter(Annotation.frame_id == frame.id)
                        .all()
                    )
                    if annotations:
                        logger.info(
                            f"Export: Frame {frame.frame_number} (id={frame.id}) has {len(annotations)} annotations"
                        )

                    if annotations:  # Only include frames with annotations
                        frame_data = {
                            "frame_number": frame.frame_number,
                            "width": frame.width,
                            "height": frame.height,
                            "video_id": video.id,
                            "video_filename": video.filename,
                            "annotations": [],
                        }

                        for anno in annotations:
                            # Get category name
                            category = (
                                db.query(Category)
                                .filter(Category.id == anno.category_id)
                                .first()
                            )

                            # Fetch mask data from MinIO storage
                            mask_bytes = None
                            if anno.mask_storage_key:
                                try:
                                    mask_bytes = storage_service.get_mask_data(
                                        anno.mask_storage_key
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to fetch mask {anno.mask_storage_key}: {e}"
                                    )

                            frame_data["annotations"].append(
                                {
                                    "id": anno.id,
                                    "category_id": anno.category_id,
                                    "category_name": category.name
                                    if category
                                    else "unknown",
                                    "mask_bytes": mask_bytes,  # Raw PNG bytes from MinIO
                                    "mask_storage_key": anno.mask_storage_key,
                                    "confidence": anno.confidence,
                                    "sam_points": anno.sam_points,
                                    "sam_boxes": anno.sam_boxes,
                                }
                            )

                        export_data["frames"].append(frame_data)

            # Debug: count total annotations
            total_annotations = sum(
                len(f["annotations"]) for f in export_data["frames"]
            )
            masks_found = sum(
                1
                for f in export_data["frames"]
                for a in f["annotations"]
                if a.get("mask_bytes")
            )

            logger.info(
                f"Prepared export data: {len(export_data['frames'])} frames, "
                f"{len(export_data['categories'])} categories, "
                f"{total_annotations} annotations, "
                f"{masks_found} masks fetched from MinIO"
            )
            return export_data

        finally:
            db.close()


# Global export service instance
export_service = ExportService()
