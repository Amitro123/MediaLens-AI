from pathlib import Path
from typing import List, Dict, Optional
import logging
import uuid
import subprocess
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ClipRequest(BaseModel):
    video_path: str
    start_time: float
    end_time: float
    output_format: str = "vertical"  # vertical (9:16), square (1:1), horizontal (16:9)

class ClipGenerator:
    """Generate short video clips from full episodes."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("uploads/clips")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def create_clip(
        self,
        episode_path: str,
        start_time: float,  # Seconds
        end_time: float,    # Seconds
        output_format: str = "vertical"  # vertical/square/horizontal
    ) -> str:
        """Extract clip and optimize for social media."""
        try:
            episode_path_obj = Path(episode_path)
            if not episode_path_obj.exists():
                raise FileNotFoundError(f"Video file not found: {episode_path}")

            clip_id = str(uuid.uuid4())[:8]
            output_filename = f"clip_{clip_id}_{output_format}.mp4"
            output_path = self.output_dir / output_filename
            
            duration = end_time - start_time
            if duration <= 0:
                raise ValueError("End time must be greater than start time")

            # Basic ffmpeg command construction
            # -ss before -i for faster seeking
            command = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', str(episode_path),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-strict', 'experimental',
                '-y' # Overwrite
            ]

            # Apply filters based on output format
            filters = []
            
            if output_format == "vertical":
                # Crop to 9:16 (assuming 16:9 input)
                # iw=input width, ih=input height
                # For 1920x1080 -> crop to 608x1080 (centered)
                filters.append("crop=ih*(9/16):ih:(iw-ow)/2:0")
            elif output_format == "square":
                 # Crop to 1:1
                 filters.append("crop=ih:ih:(iw-ow)/2:0")
            
            if filters:
                 command.extend(['-vf', ",".join(filters)])

            command.append(str(output_path))
            
            logger.info(f"Generating clip: {command}")
            
            # Execute ffmpeg
            # Using run in threadpool usually recommended for blocking IO, strictly speaking subprocess is blocking
            # but for MVP synchronous subprocess run is okay or use asyncio.create_subprocess_exec
            proc = subprocess.run(
                command, 
                capture_output=True, 
                text=True,
                check=True
            )
            
            logger.info(f"Clip generated at {output_path}")
            return str(output_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr}")
            raise RuntimeError(f"Failed to generate clip: {e.stderr}")
        except Exception as e:
            logger.error(f"Error generating clip: {e}")
            raise
