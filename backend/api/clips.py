from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
import uuid
import os
from pathlib import Path

from core.video_clip import VideoClip
from core.config import AppConfig

router = APIRouter()

# In-memory clip storage (in production, use database)
clips_storage: Dict[str, VideoClip] = {}

@router.post("/upload")
async def upload_clip(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a video clip"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in AppConfig.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_extension} not allowed. Allowed types: {AppConfig.ALLOWED_EXTENSIONS}"
        )
    
    # Generate unique ID and filename
    clip_id = str(uuid.uuid4())
    safe_filename = f"{clip_id}_{file.filename}"
    filepath = os.path.join(AppConfig.UPLOAD_DIR, safe_filename)
    
    # Ensure upload directory exists
    AppConfig.ensure_directories()
    
    try:
        # Save uploaded file
        with open(filepath, "wb") as buffer:
            content = await file.read()
            
            # Check file size
            if len(content) > AppConfig.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File too large. Maximum size: {AppConfig.MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            buffer.write(content)
        
        # Create VideoClip instance
        clip = VideoClip(
            id=clip_id,
            filename=file.filename,
            filepath=filepath
        )
        
        # Store in memory
        clips_storage[clip_id] = clip
        
        return {
            "success": True,
            "clip": clip.get_info_dict()
        }
        
    except Exception as e:
        # Clean up file if something went wrong
        if os.path.exists(filepath):
            os.remove(filepath)
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/")
async def get_clips() -> Dict[str, Any]:
    """Get all uploaded clips"""
    clips = [clip.get_info_dict() for clip in clips_storage.values()]
    return {
        "clips": clips,
        "count": len(clips)
    }

@router.get("/{clip_id}")
async def get_clip(clip_id: str) -> Dict[str, Any]:
    """Get a specific clip"""
    if clip_id not in clips_storage:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    clip = clips_storage[clip_id]
    return clip.get_info_dict()

@router.delete("/{clip_id}")
async def delete_clip(clip_id: str) -> Dict[str, Any]:
    """Delete a clip"""
    if clip_id not in clips_storage:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    clip = clips_storage[clip_id]
    
    # Clean up file
    clip.cleanup()
    
    # Remove from storage
    del clips_storage[clip_id]
    
    return {"success": True, "message": f"Clip {clip_id} deleted"}

@router.delete("/")
async def clear_all_clips() -> Dict[str, Any]:
    """Clear all clips"""
    # Clean up all files
    for clip in clips_storage.values():
        clip.cleanup()
    
    # Clear storage
    clips_storage.clear()
    
    return {"success": True, "message": "All clips cleared"}

@router.post("/reorder")
async def reorder_clips(clip_ids: List[str]) -> Dict[str, Any]:
    """Reorder clips (for future drag & drop functionality)"""
    # Validate all clip IDs exist
    for clip_id in clip_ids:
        if clip_id not in clips_storage:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
    
    # For now, just return success - ordering will be handled by frontend
    # In production, you might want to store order in database
    return {
        "success": True, 
        "message": f"Clips reordered: {clip_ids}"
    }