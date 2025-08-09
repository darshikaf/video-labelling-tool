import os
import shutil
from pathlib import Path
from typing import List
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.db.database import get_db

router = APIRouter()


def process_video_metadata(file_path: str) -> dict:
    """Extract metadata from video file using OpenCV"""
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise ValueError("Could not open video file")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else None
        
        cap.release()
        
        return {
            'fps': fps,
            'total_frames': total_frames,
            'width': width,
            'height': height,
            'duration': duration
        }
    except Exception as e:
        print(f"Error processing video metadata: {e}")
        return {}




@router.get("/{video_id}", response_model=schemas.Video)
def read_video(
    video_id: int,
    db: Session = Depends(get_db),
):
    video = crud.video.get(db=db, id=video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/frames/{frame_number}")
def get_video_frame(
    video_id: int,
    frame_number: int,
    db: Session = Depends(get_db),
):
    video = crud.video.get(db=db, id=video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    try:
        cap = cv2.VideoCapture(video.file_path)
        if not cap.isOpened():
            # Return a placeholder frame for invalid video files
            import numpy as np
            placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Add text to indicate this is a placeholder
            cv2.putText(placeholder_frame, "Invalid Video File", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(placeholder_frame, f"Frame {frame_number}", (250, 280), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
            
            success, buffer = cv2.imencode('.jpg', placeholder_frame)
            if not success:
                raise HTTPException(status_code=500, detail="Could not create placeholder frame")
                
            return Response(
                content=buffer.tobytes(),
                media_type="image/jpeg",
                headers={"Cache-Control": "max-age=3600"}
            )
        
        # Validate frame number
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            # Handle videos with unknown frame count
            cap.release()
            # Return placeholder as above
            import numpy as np
            placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder_frame, "Video Processing Error", (180, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            success, buffer = cv2.imencode('.jpg', placeholder_frame)
            return Response(content=buffer.tobytes(), media_type="image/jpeg")
            
        if frame_number < 0 or frame_number >= total_frames:
            cap.release()
            raise HTTPException(status_code=400, detail="Invalid frame number")
        
        # Seek to frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            # Return placeholder frame if can't read specific frame
            import numpy as np
            placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder_frame, "Frame Read Error", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            success, buffer = cv2.imencode('.jpg', placeholder_frame)
            return Response(content=buffer.tobytes(), media_type="image/jpeg")
        
        # Encode frame as JPEG
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            raise HTTPException(status_code=500, detail="Could not encode frame")
        
        return Response(
            content=buffer.tobytes(),
            media_type="image/jpeg",
            headers={"Cache-Control": "max-age=3600"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting frame: {str(e)}")


@router.delete("/{video_id}")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
):
    video = crud.video.get(db=db, id=video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete video file
    try:
        if os.path.exists(video.file_path):
            os.remove(video.file_path)
    except Exception as e:
        print(f"Warning: Could not delete video file {video.file_path}: {e}")
    
    # Delete database record
    crud.video.remove(db=db, id=video_id)
    
    return {"message": "Video deleted successfully"}