from pydantic import BaseModel
from typing import Optional, Dict, Any
import cv2
import os
import subprocess
import base64
from pathlib import Path

class VideoClip(BaseModel):
    """Represents a video clip with metadata and operations"""
    
    id: str
    filename: str
    filepath: str
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    has_audio: Optional[bool] = None
    file_size: Optional[int] = None
    thumbnail_base64: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.filepath and os.path.exists(self.filepath):
            self._extract_metadata()
            self._generate_thumbnail()
    
    def _extract_metadata(self):
        """Extract video metadata using OpenCV and FFprobe"""
        try:
            # Use OpenCV for basic metadata
            cap = cv2.VideoCapture(self.filepath)
            if cap.isOpened():
                self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.fps = cap.get(cv2.CAP_PROP_FPS)
                self.frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if self.fps > 0:
                    self.duration = self.frame_count / self.fps
                cap.release()
            
            # Get file size
            self.file_size = os.path.getsize(self.filepath)
            
            # Check for audio using FFprobe
            self.has_audio = self._check_audio_stream()
            
        except Exception as e:
            print(f"Error extracting metadata for {self.filepath}: {e}")
    
    def _check_audio_stream(self) -> bool:
        """Check if video file has audio stream using FFprobe"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-select_streams", "a:0", 
                "-show_entries", "stream=index", "-of", "csv=p=0", self.filepath
            ], capture_output=True, text=True, check=True)
            return bool(result.stdout.strip())
        except:
            return False
    
    def _generate_thumbnail(self, timestamp: float = 1.0):
        """Generate thumbnail at specified timestamp"""
        try:
            cap = cv2.VideoCapture(self.filepath)
            if not cap.isOpened():
                return
            
            # Seek to timestamp (in seconds)
            if self.duration and timestamp > self.duration:
                timestamp = self.duration / 2
            
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Resize thumbnail to reasonable size
                height, width = frame.shape[:2]
                if width > 320:
                    scale = 320 / width
                    new_width = 320
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # Convert to base64 for web display
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                self.thumbnail_base64 = base64.b64encode(buffer).decode('utf-8')
                
        except Exception as e:
            print(f"Error generating thumbnail for {self.filepath}: {e}")
    
    def get_info_dict(self) -> Dict[str, Any]:
        """Get clip information as dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "has_audio": self.has_audio,
            "file_size": self.file_size,
            "thumbnail": f"data:image/jpeg;base64,{self.thumbnail_base64}" if self.thumbnail_base64 else None
        }
    
    def cleanup(self):
        """Remove the video file"""
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
        except Exception as e:
            print(f"Error cleaning up {self.filepath}: {e}")