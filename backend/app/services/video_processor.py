"""Video processing service for frame extraction and audio analysis"""

import cv2
from pathlib import Path
from typing import List, Optional
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

# Import tracing decorator
from app.core.observability import trace_pipeline


class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    pass


@trace_pipeline
def create_low_fps_proxy(video_path: str, output_dir: Optional[str] = None, fps: int = 1) -> str:
    """
    Create a low-FPS version of the video specifically for multimodal analysis.
    This drastically reduces token count while maintaining semantic context.
    
    Args:
        video_path: Path to the input video file
        output_dir: Optional directory to save proxy (defaults to task directory)
        fps: Target frame rate (default: 1 FPS)
    
    Returns:
        Path to the generated low-FPS proxy video
    """
    try:
        video_path_obj = Path(video_path)
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = video_path_obj.parent
            
        proxy_filename = f"{video_path_obj.stem}_proxy_1fps.mp4"
        proxy_path = output_path / proxy_filename
        
        # FFmpeg command to drop frames to 1 FPS and lower resolution/quality for analysis speed
        # -r 1: Set output frame rate
        # -vf scale=640:-2: Scale to 640px width (maintaining aspect ratio, ensuring width is even)
        # -crf 28: Lower quality/higher compression
        # -preset veryfast: Faster encoding
        command = [
            'ffmpeg',
            '-i', str(video_path),
            '-filter:v', f'fps={fps},scale=640:-2',
            '-c:v', 'libx264',
            '-crf', '28',
            '-preset', 'veryfast',
            '-an', # Skip audio, we extract audio separately if needed
            '-y',
            str(proxy_path)
        ]
        
        logger.info(f"Creating {fps} FPS proxy for {video_path}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not proxy_path.exists():
            raise VideoProcessingError("Video proxy was not created")
            
        logger.info(f"Proxy created at {proxy_path}")
        return str(proxy_path)
        
    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(f"FFmpeg proxy error: {e.stderr}")
    except Exception as e:
        raise VideoProcessingError(f"Failed to create video proxy: {str(e)}")


@trace_pipeline
def extract_audio(video_path: str, output_dir: Optional[str] = None) -> str:
    """
    Extract audio track from a video file.
    
    Args:
        video_path: Path to the input video file
        output_dir: Optional directory to save audio file (defaults to video directory)
    
    Returns:
        Path to the extracted audio file (WAV format)
    
    Raises:
        VideoProcessingError: If audio extraction fails
    """
    try:
        video_path_obj = Path(video_path)
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = video_path_obj.parent
        
        # Output audio file path
        audio_filename = f"{video_path_obj.stem}_audio.wav"
        audio_path = output_path / audio_filename
        
        # Use ffmpeg to extract audio
        # -vn: no video, -acodec pcm_s16le: WAV format, -ar 16000: 16kHz sample rate
        command = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV codec
            '-ar', '16000',  # 16kHz sample rate (good for speech)
            '-ac', '1',  # Mono channel
            '-y',  # Overwrite output file
            str(audio_path)
        ]
        
        logger.info(f"Extracting audio from {video_path}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not audio_path.exists():
            raise VideoProcessingError("Audio file was not created")
        
        logger.info(f"Audio extracted to {audio_path}")
        
        return str(audio_path)
    
    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(f"FFmpeg error: {e.stderr}")
    except Exception as e:
        raise VideoProcessingError(f"Failed to extract audio: {str(e)}")


def extract_frames_at_timestamps(
    video_path: str,
    output_dir: str,
    timestamps: List[float]
) -> List[str]:
    """
    Extract frames from a video at specific timestamps.
    
    Args:
        video_path: Path to the input video file
        output_dir: Directory to save extracted frames
        timestamps: List of timestamps (in seconds) to extract frames at
    
    Returns:
        List of paths to extracted frame images
    
    Raises:
        VideoProcessingError: If video cannot be processed
    """
    frame_paths = []
    
    try:
        # Open video file
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            raise VideoProcessingError(f"Failed to open video file: {video_path}")
        
        # Get video properties
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Processing video: {duration:.2f}s, {fps:.2f} FPS")
        logger.info(f"Extracting frames at {len(timestamps)} timestamps")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Sort timestamps to process in order
        sorted_timestamps = sorted(timestamps)
        
        # Extract frames at each timestamp
        for idx, timestamp in enumerate(sorted_timestamps):
            # Skip timestamps beyond video duration
            if timestamp > duration:
                logger.warning(f"Timestamp {timestamp}s exceeds video duration {duration:.2f}s, skipping")
                continue
            
            # Calculate frame number
            frame_number = int(timestamp * fps)
            
            # Seek to frame
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = video.read()
            
            if not ret:
                logger.warning(f"Failed to read frame at {timestamp}s")
                continue
            
            # Save frame
            frame_filename = f"frame_{idx:04d}_t{timestamp:.1f}s.jpg"
            frame_path = output_path / frame_filename
            
            cv2.imwrite(str(frame_path), frame)
            frame_paths.append(str(frame_path))
            
            logger.debug(f"Extracted frame {idx + 1} at {timestamp:.2f}s")
        
        video.release()
        
        logger.info(f"Extracted {len(frame_paths)} frames from video")
        
        if not frame_paths:
            raise VideoProcessingError("No frames were extracted from the video")
        
        return frame_paths
    
    except cv2.error as e:
        raise VideoProcessingError(f"OpenCV error: {str(e)}")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during frame extraction: {str(e)}")


@trace_pipeline
def extract_frames(
    video_path: str,
    output_dir: str,
    interval: int = 5,
    timestamps: Optional[List[float]] = None
) -> List[str]:
    """
    Extract frames from a video file.
    
    If timestamps are provided, extracts frames at those specific times.
    Otherwise, extracts frames at regular intervals.
    
    Args:
        video_path: Path to the input video file
        output_dir: Directory to save extracted frames
        interval: Extract 1 frame every N seconds (default: 5) - used only if timestamps is None
        timestamps: Optional list of specific timestamps (in seconds) to extract frames at
    
    Returns:
        List of paths to extracted frame images
    
    Raises:
        VideoProcessingError: If video cannot be processed
    """
    # Use timestamp-based extraction if timestamps provided
    if timestamps is not None:
        return extract_frames_at_timestamps(video_path, output_dir, timestamps)
    
    # Otherwise use interval-based extraction (legacy behavior)
    frame_paths = []
    
    try:
        # Open video file
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            raise VideoProcessingError(f"Failed to open video file: {video_path}")
        
        # Get video properties
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Processing video: {duration:.2f}s, {fps:.2f} FPS, {total_frames} frames")
        
        # Calculate frame interval
        frame_interval = int(fps * interval)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Extract frames
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = video.read()
            
            if not ret:
                break
            
            # Save frame at intervals
            if frame_count % frame_interval == 0:
                frame_filename = f"frame_{saved_count:04d}.jpg"
                frame_path = output_path / frame_filename
                
                cv2.imwrite(str(frame_path), frame)
                frame_paths.append(str(frame_path))
                saved_count += 1
                
                logger.debug(f"Extracted frame {saved_count} at {frame_count / fps:.2f}s")
            
            frame_count += 1
        
        video.release()
        
        logger.info(f"Extracted {saved_count} frames from video")
        
        if not frame_paths:
            raise VideoProcessingError("No frames were extracted from the video")
        
        return frame_paths
    
    except cv2.error as e:
        raise VideoProcessingError(f"OpenCV error: {str(e)}")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during frame extraction: {str(e)}")


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds.
    
    Args:
        video_path: Path to the video file
    
    Returns:
        Duration in seconds
    
    Raises:
        VideoProcessingError: If video cannot be read
    """
    try:
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            raise VideoProcessingError(f"Failed to open video file: {video_path}")
        
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        video.release()
        
        return duration
    
    except Exception as e:
        raise VideoProcessingError(f"Failed to get video duration: {str(e)}")

