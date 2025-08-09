import os
import io
import base64
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error
from app.core.config import settings

class StorageService:
    """Service for handling object storage operations with MinIO/S3"""
    
    def __init__(self):
        self.client = self._create_client()
        self.bucket_name = self._get_bucket_name()
        self._ensure_bucket_exists()
    
    def _create_client(self) -> Minio:
        """Create MinIO client from environment variables"""
        endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        
        return Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
    
    def _get_bucket_name(self) -> str:
        """Get bucket name from environment"""
        return os.getenv('MINIO_BUCKET', 'video-annotations')
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")
            raise
    
    def store_mask(self, project_id: int, video_id: int, frame_number: int, 
                   annotation_id: int, mask_data: str) -> str:
        """
        Store mask data in object storage
        
        Args:
            project_id: ID of the project
            video_id: ID of the video
            frame_number: Frame number
            annotation_id: ID of the annotation
            mask_data: Base64 encoded mask image data
            
        Returns:
            Object key/path in storage
        """
        try:
            # Create object key with hierarchical structure
            object_key = f"projects/{project_id}/videos/{video_id}/frames/{frame_number}/annotations/{annotation_id}/mask.png"
            
            # Decode base64 mask data
            if mask_data.startswith('data:image'):
                # Remove data URL prefix if present
                mask_data = mask_data.split(',')[1]
            
            mask_bytes = base64.b64decode(mask_data)
            
            # Upload to storage
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=io.BytesIO(mask_bytes),
                length=len(mask_bytes),
                content_type='image/png'
            )
            
            return object_key
            
        except Exception as e:
            print(f"Error storing mask: {e}")
            raise
    
    def get_mask_url(self, object_key: str, expires_in_hours: int = 24) -> str:
        """
        Get presigned URL for mask retrieval
        
        Args:
            object_key: Object key/path in storage
            expires_in_hours: URL expiration time in hours
            
        Returns:
            Presigned URL for accessing the mask
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                expires=timedelta(hours=expires_in_hours)
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            raise
    
    def delete_mask(self, object_key: str) -> bool:
        """
        Delete mask from object storage
        
        Args:
            object_key: Object key/path in storage
            
        Returns:
            True if deletion was successful
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_key
            )
            return True
        except Exception as e:
            print(f"Error deleting mask: {e}")
            return False
    
    def store_frame_image(self, project_id: int, video_id: int, frame_number: int, 
                         image_data: bytes) -> str:
        """
        Store frame image in object storage
        
        Args:
            project_id: ID of the project
            video_id: ID of the video
            frame_number: Frame number
            image_data: Binary image data
            
        Returns:
            Object key/path in storage
        """
        try:
            # Create object key
            object_key = f"projects/{project_id}/videos/{video_id}/frames/{frame_number}/image.jpg"
            
            # Upload to storage
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=io.BytesIO(image_data),
                length=len(image_data),
                content_type='image/jpeg'
            )
            
            return object_key
            
        except Exception as e:
            print(f"Error storing frame image: {e}")
            raise
    
    def get_frame_url(self, object_key: str, expires_in_hours: int = 24) -> str:
        """
        Get presigned URL for frame image retrieval
        
        Args:
            object_key: Object key/path in storage
            expires_in_hours: URL expiration time in hours
            
        Returns:
            Presigned URL for accessing the frame image
        """
        return self.get_mask_url(object_key, expires_in_hours)
    
    def store_annotation(self, project_id: int, video_id: int, frame_number: int, 
                        annotation_id: int, annotation_content: str, format_type: str) -> str:
        """
        Store annotation file in object storage
        
        Args:
            project_id: ID of the project
            video_id: ID of the video
            frame_number: Frame number
            annotation_id: ID of the annotation
            annotation_content: Formatted annotation content (YOLO, COCO, etc.)
            format_type: Annotation format type (YOLO, COCO, PASCAL_VOC)
            
        Returns:
            Object key/path in storage
        """
        try:
            # Get file extension based on format
            extensions = {
                'YOLO': '.txt',
                'COCO': '.json',
                'PASCAL_VOC': '.xml'
            }
            ext = extensions.get(format_type.upper(), '.txt')
            
            # Create object key
            object_key = f"projects/{project_id}/videos/{video_id}/frames/{frame_number}/annotations/{annotation_id}/annotation{ext}"
            
            # Convert content to bytes
            content_bytes = annotation_content.encode('utf-8')
            
            # Determine content type
            content_types = {
                '.txt': 'text/plain',
                '.json': 'application/json',
                '.xml': 'application/xml'
            }
            content_type = content_types.get(ext, 'text/plain')
            
            # Upload to storage
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=io.BytesIO(content_bytes),
                length=len(content_bytes),
                content_type=content_type
            )
            
            return object_key
            
        except Exception as e:
            print(f"Error storing annotation: {e}")
            raise
    
    def store_mask_and_annotation(self, project_id: int, video_id: int, frame_number: int,
                                 annotation_id: int, mask_data: str, annotation_content: str, 
                                 format_type: str) -> dict:
        """
        Store both mask and annotation files in object storage
        
        Args:
            project_id: ID of the project
            video_id: ID of the video
            frame_number: Frame number
            annotation_id: ID of the annotation
            mask_data: Base64 encoded mask image data
            annotation_content: Formatted annotation content
            format_type: Annotation format type
            
        Returns:
            Dict with both storage keys
        """
        try:
            # Store mask
            mask_key = self.store_mask(project_id, video_id, frame_number, annotation_id, mask_data)
            
            # Store annotation
            annotation_key = self.store_annotation(project_id, video_id, frame_number, 
                                                 annotation_id, annotation_content, format_type)
            
            return {
                'mask_storage_key': mask_key,
                'annotation_storage_key': annotation_key
            }
            
        except Exception as e:
            print(f"Error storing mask and annotation: {e}")
            raise
    
    def get_annotation_url(self, object_key: str, expires_in_hours: int = 24) -> str:
        """
        Get presigned URL for annotation file retrieval
        
        Args:
            object_key: Object key/path in storage
            expires_in_hours: URL expiration time in hours
            
        Returns:
            Presigned URL for accessing the annotation file
        """
        return self.get_mask_url(object_key, expires_in_hours)

# Global instance
storage_service = StorageService()