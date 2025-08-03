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

# Global instance
storage_service = StorageService()