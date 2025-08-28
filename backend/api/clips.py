from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path
import subprocess
import uuid
from typing import List
from pydantic import BaseModel

class ConcatenateRequest(BaseModel):
    clip_ids: List[str]
    output_filename: str = None  # Optional, we'll generate if not provided

router = APIRouter(prefix="/api/clips")

# In-memory storage for clip metadata
clips = {}
clip_counter = 0

# Create directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

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

@router.get("/")
async def list_clips():
    return {"clips": list(clips.values())}

@router.get("/{clip_id}/video")
async def get_clip_video(clip_id: str):
    if clip_id not in clips:
        raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
    
    clip = clips[clip_id]
    file_path = clip["file_path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=clip["filename"]
    )

@router.get("/output/{filename}")
async def get_output_video(filename: str):
    output_path = OUTPUT_DIR / filename
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=filename
    )

@router.post("/concatenate")
async def concatenate_clips(request: ConcatenateRequest):
    if not request.clip_ids:
        raise HTTPException(status_code=400, detail="No clips provided")
    
    # Validate all clips exist
    for clip_id in request.clip_ids:
        if clip_id not in clips:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
    
    # Generate output filename
    if request.output_filename:
        output_filename = request.output_filename
        if not output_filename.endswith('.mp4'):
            output_filename += '.mp4'
    else:
        output_filename = f"{uuid.uuid4().hex}.mp4"
    
    output_path = OUTPUT_DIR / output_filename
    
    # Get file paths in order
    input_files = [clips[clip_id]["file_path"] for clip_id in request.clip_ids]
    
    if len(input_files) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 clips to concatenate")
    
    # Check if first video has audio (assuming all have same audio setup for now)
    def has_audio_stream(video_file):
        try:
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-select_streams", "a:0", 
                "-show_entries", "stream=index", "-of", "csv=p=0", video_file
            ], capture_output=True, text=True, check=True)
            return bool(result.stdout.strip())
        except:
            return False
    
    has_audio = has_audio_stream(input_files[0])
    
    # Build FFmpeg command (adapted from joiner.py)
    cmd = ["ffmpeg", "-y"]  # -y to overwrite output file
    
    # Add all input files
    for video in input_files:
        cmd.extend(["-i", video])
    
    # Build filter complex
    filter_parts = []
    concat_inputs = []
    
    for i, _ in enumerate(input_files):
        if i == 0:
            # First video: use as-is
            concat_inputs.append(f"[{i}:v]")
            if has_audio:
                concat_inputs.append(f"[{i}:a]")
        else:
            # Subsequent videos: trim first frame (0.0625s for 16fps)
            filter_parts.append(f"[{i}:v]trim=start_frame=1[{i}vtrim]")
            concat_inputs.append(f"[{i}vtrim]")
            if has_audio:
                filter_parts.append(f"[{i}:a]atrim=start=0.0625[{i}atrim]")
                concat_inputs.append(f"[{i}atrim]")
    
    # Combine all parts
    filter_complex = ";".join(filter_parts)
    if filter_parts:
        filter_complex += ";"
    
    # Build concat filter
    if has_audio:
        filter_complex += "".join(concat_inputs) + f"concat=n={len(input_files)}:v=1:a=1[outv][outa]"
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[outv]", "-map", "[outa]", str(output_path)])
    else:
        filter_complex += "".join(concat_inputs) + f"concat=n={len(input_files)}:v=1:a=0[outv]"
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[outv]", str(output_path)])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {
            "message": "Clips concatenated successfully",
            "output_filename": output_filename,
            "output_path": str(output_path),
            "had_audio": has_audio,
            "clips_processed": len(input_files)
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr}")