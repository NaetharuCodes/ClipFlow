import subprocess
import os
import asyncio
from typing import List, Optional, Callable
from .video_clip import VideoClip
from .config import ProcessingConfig

class VideoProcessor:
    """Handles video concatenation using FFmpeg - based on your original joiner.py"""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
    
    async def concatenate_videos(
        self, 
        clips: List[VideoClip], 
        output_path: str, 
        config: ProcessingConfig
    ) -> bool:
        """
        Concatenate multiple video clips - adapted from your joiner.py logic
        """
        if len(clips) < 1:
            raise ValueError("Need at least 1 clip to process")
        
        # Check if videos have audio (use first clip as reference)
        has_audio = clips[0].has_audio if clips else False
        
        if self.progress_callback:
            await self.progress_callback({"stage": "preparing", "progress": 0})
        
        # Build FFmpeg command
        cmd = self._build_ffmpeg_command(clips, output_path, config, has_audio)
        
        if self.progress_callback:
            await self.progress_callback({"stage": "processing", "progress": 10})
        
        # Execute FFmpeg command
        success = await self._execute_ffmpeg(cmd)
        
        if self.progress_callback:
            await self.progress_callback({
                "stage": "complete" if success else "error", 
                "progress": 100 if success else 0
            })
        
        return success
    
    def _build_ffmpeg_command(
        self, 
        clips: List[VideoClip], 
        output_path: str, 
        config: ProcessingConfig, 
        has_audio: bool
    ) -> List[str]:
        """Build FFmpeg command - adapted from your original logic"""
        
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output file
        
        # Add all input files
        for clip in clips:
            cmd.extend(["-i", clip.filepath])
        
        # Build filter complex for trimming frames
        filter_parts = []
        concat_inputs = []
        
        for i, clip in enumerate(clips):
            if i == 0:
                # First video: use as-is (unless trim_start_frames is set)
                if config.trim_start_frames > 0:
                    trim_time = config.trim_start_frames / config.framerate
                    filter_parts.append(f"[{i}:v]trim=start={trim_time}[{i}vtrim]")
                    concat_inputs.append(f"[{i}vtrim]")
                    if has_audio:
                        filter_parts.append(f"[{i}:a]atrim=start={trim_time}[{i}atrim]")
                        concat_inputs.append(f"[{i}atrim]")
                else:
                    concat_inputs.append(f"[{i}:v]")
                    if has_audio:
                        concat_inputs.append(f"[{i}:a]")
            else:
                # Subsequent videos: trim first frame + any additional frames
                total_start_frames = 1 + config.trim_start_frames
                trim_time = total_start_frames / config.framerate
                
                filter_parts.append(f"[{i}:v]trim=start={trim_time}[{i}vtrim]")
                concat_inputs.append(f"[{i}vtrim]")
                
                if has_audio:
                    filter_parts.append(f"[{i}:a]atrim=start={trim_time}[{i}atrim]")
                    concat_inputs.append(f"[{i}atrim]")
        
        # Build complete filter complex
        filter_complex = ";".join(filter_parts)
        if filter_parts:
            filter_complex += ";"
        
        # Add concat filter
        if has_audio:
            filter_complex += "".join(concat_inputs) + f"concat=n={len(clips)}:v=1:a=1[outv][outa]"
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", "[outv]", "-map", "[outa]"])
        else:
            filter_complex += "".join(concat_inputs) + f"concat=n={len(clips)}:v=1:a=0[outv]"
            cmd.extend(["-filter_complex", filter_complex])
            cmd.extend(["-map", "[outv]"])
        
        # Add encoding options
        cmd.extend(["-c:v", config.codec])
        
        # Quality preset
        if config.codec in ["libx264", "libx265"]:
            cmd.extend(["-preset", config.quality])
        
        # Framerate
        cmd.extend(["-r", str(config.framerate)])
        
        # Resolution
        if config.resolution:
            cmd.extend(["-s", config.resolution])
        
        # Bitrate
        if config.bitrate:
            cmd.extend(["-b:v", config.bitrate])
        
        # Audio settings
        if has_audio:
            cmd.extend(["-c:a", config.audio_codec])
            if config.audio_bitrate:
                cmd.extend(["-b:a", config.audio_bitrate])
        
        # Custom FFmpeg arguments
        cmd.extend(config.custom_ffmpeg_args)
        
        # Output file
        cmd.append(output_path)
        
        return cmd
    
    async def _execute_ffmpeg(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command asynchronously"""
        try:
            print(f"Executing FFmpeg command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ FFmpeg completed successfully")
                return True
            else:
                print(f"❌ FFmpeg failed with return code {process.returncode}")
                print(f"Error output: {stderr.decode()}")
                return False
                
        except FileNotFoundError:
            print("❌ Error: FFmpeg not found. Please install FFmpeg and make sure it's in your PATH.")
            return False
        except Exception as e:
            print(f"❌ FFmpeg execution error: {e}")
            return False