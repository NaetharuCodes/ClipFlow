from fastapi import APIRouter, File, UploadFile, HTTPException
import os
import shutil
from pathlib import Path

router = APIRouter(prefix="/api/clips")

# Storing clips in memory as they are small (~2MB per clip)
clips = {}
clip_counter = 0

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_clip(file: UploadFile = File(...)):
    global clip_counter
    
    # Generate simple clip ID
    clip_counter += 1
    clip_id = f"clip_{clip_counter}"
    
    # Save file to uploads directory
    file_path = UPLOAD_DIR / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Store metadata in memory
    clips[clip_id] = {
        "id": clip_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "file_size": file_path.stat().st_size
    }
    
    return {"message": "File uploaded successfully", "clip": clips[clip_id]}