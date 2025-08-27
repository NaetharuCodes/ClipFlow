from pydantic import BaseModel
from typing import Optional, List
import os

class ProcessingConfig(BaseModel):
    """Configuration for video processing"""
    # Video settings
    codec: str = "libx264"
    quality: str = "medium"  # fast, medium, slow, veryslow
    resolution: Optional[str] = None  # None for original, or "1920x1080", "1280x720", etc.
    framerate: float = 16.0
    bitrate: Optional[str] = None  # e.g. "2M", "1000k"
    
    # Audio settings
    audio_codec: str = "aac"
    audio_bitrate: Optional[str] = "128k"
    
    # Processing options
    trim_start_frames: int = 0  # Frames to trim from start of each clip (except first)
    trim_end_frames: int = 0    # Frames to trim from end of each clip
    
    # FFmpeg options
    custom_ffmpeg_args: List[str] = []

class AppConfig:
    """Global application configuration"""
    UPLOAD_DIR = "uploads"
    OUTPUT_DIR = "output"
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}
    
    # Default processing config
    DEFAULT_PROCESSING = ProcessingConfig()
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)