from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import os
import uuid
from datetime import datetime

from core.processor import VideoProcessor
from core.config import ProcessingConfig, AppConfig
from api.clips import clips_storage

router = APIRouter()

class ProcessingRequest(BaseModel):
    clip_ids: List[str]
    output_filename: Optional[str] = None
    config: Optional[ProcessingConfig] = None

# Active WebSocket connections for progress updates
active_connections: List[WebSocket] = []

@router.websocket("/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_progress(message: Dict[str, Any]):
    """Broadcast progress to all connected clients"""
    if active_connections:
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            active_connections.remove(conn)

@router.post("/concatenate")
async def start_concatenation(request: ProcessingRequest) -> Dict[str, Any]:
    """Start video concatenation process"""
    
    # Validate clip IDs
    if not request.clip_ids:
        raise HTTPException(status_code=400, detail="No clips provided")
    
    clips = []
    for clip_id in request.clip_ids:
        if clip_id not in clips_storage:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
        clips.append(clips_storage[clip_id])
    
    # Generate output filename
    if not request.output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        request.output_filename = f"concatenated_{timestamp}.mp4"
    
    # Ensure output filename has .mp4 extension
    if not request.output_filename.endswith('.mp4'):
        request.output_filename += '.mp4'
    
    output_path = os.path.join(AppConfig.OUTPUT_DIR, request.output_filename)
    
    # Use default config if none provided
    config = request.config or AppConfig.DEFAULT_PROCESSING
    
    # Create processor with progress callback
    processor = VideoProcessor(progress_callback=broadcast_progress)
    
    # Start processing in background
    asyncio.create_task(process_videos_background(processor, clips, output_path, config))
    
    return {
        "success": True,
        "message": "Processing started",
        "output_filename": request.output_filename,
        "clip_count": len(clips)
    }

async def process_videos_background(
    processor: VideoProcessor, 
    clips: List, 
    output_path: str, 
    config: ProcessingConfig
):
    """Background task to process videos"""
    try:
        await broadcast_progress({
            "stage": "starting",
            "progress": 0,
            "message": f"Starting concatenation of {len(clips)} clips"
        })
        
        success = await processor.concatenate_videos(clips, output_path, config)
        
        if success:
            # Get output file info
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            await broadcast_progress({
                "stage": "complete",
                "progress": 100,
                "message": "Concatenation completed successfully",
                "output_path": output_path,
                "output_filename": os.path.basename(output_path),
                "file_size": file_size
            })
        else:
            await broadcast_progress({
                "stage": "error",
                "progress": 0,
                "message": "Concatenation failed"
            })
            
    except Exception as e:
        await broadcast_progress({
            "stage": "error",
            "progress": 0,
            "message": f"Error during processing: {str(e)}"
        })

@router.get("/status")
async def get_processing_status() -> Dict[str, Any]:
    """Get current processing status"""
    # In a real implementation, you'd track active jobs
    return {
        "active_jobs": 0,
        "connected_clients": len(active_connections)
    }

@router.get("/outputs")
async def list_outputs() -> Dict[str, Any]:
    """List available output files"""
    try:
        AppConfig.ensure_directories()
        
        outputs = []
        if os.path.exists(AppConfig.OUTPUT_DIR):
            for filename in os.listdir(AppConfig.OUTPUT_DIR):
                filepath = os.path.join(AppConfig.OUTPUT_DIR, filename)
                if os.path.isfile(filepath):
                    outputs.append({
                        "filename": filename,
                        "size": os.path.getsize(filepath),
                        "modified": os.path.getmtime(filepath)
                    })
        
        return {
            "outputs": outputs,
            "count": len(outputs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing outputs: {str(e)}")

@router.delete("/outputs/{filename}")
async def delete_output(filename: str) -> Dict[str, Any]:
    """Delete an output file"""
    try:
        filepath = os.path.join(AppConfig.OUTPUT_DIR, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Output file not found")
        
        # Security check - ensure file is in output directory
        if not os.path.commonpath([filepath, AppConfig.OUTPUT_DIR]) == AppConfig.OUTPUT_DIR:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        os.remove(filepath)
        
        return {
            "success": True,
            "message": f"Output file {filename} deleted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting output: {str(e)}")