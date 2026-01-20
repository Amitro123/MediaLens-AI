"""Video processing service for frame extraction and audio analysis"""

import cv2
from pathlib import Path
from typing import List, Optional, Dict
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

# Import tracing decorator
from app.core.observability import trace_pipeline, record_event, EventType


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


def split_into_segments(video_path: str, segment_duration_sec: int = 30) -> List[Dict]:
    """
    Split video into logical segments for chunk-based processing.
    
    Args:
        video_path: Path to the input video file
        segment_duration_sec: Duration of each segment in seconds (default: 30)
    
    Returns:
        List of segment descriptors: [{"start": 0, "end": 30, "index": 0}, ...]
    
    Raises:
        VideoProcessingError: If video cannot be read
    """
    try:
        duration = get_video_duration(video_path)
        
        segments = []
        current_start = 0.0
        index = 0
        
        while current_start < duration:
            end = min(current_start + segment_duration_sec, duration)
            segments.append({
                "start": current_start,
                "end": end,
                "index": index,
                "duration": end - current_start
            })
            current_start = end
            index += 1
        
        logger.info(f"Split video ({duration:.1f}s) into {len(segments)} segments of ~{segment_duration_sec}s each")
        return segments
    
    except Exception as e:
        raise VideoProcessingError(f"Failed to split video into segments: {str(e)}")


def extract_segment_audio(
    video_path: str,
    start: float,
    end: float,
    output_dir: Optional[str] = None
) -> str:
    """
    Extract audio for a specific time range (segment).
    
    Args:
        video_path: Path to the input video file
        start: Start time in seconds
        end: End time in seconds
        output_dir: Optional directory to save audio file
    
    Returns:
        Path to the extracted audio file (WAV format)
    
    Raises:
        VideoProcessingError: If audio extraction fails
    """
    try:
        video_path_obj = Path(video_path)
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = video_path_obj.parent
        
        # Output audio file path with segment time info
        audio_filename = f"{video_path_obj.stem}_audio_seg_{start:.0f}_{end:.0f}.wav"
        audio_path = output_path / audio_filename
        
        duration = end - start
        
        # Use ffmpeg with -ss (seek) and -t (duration)
        command = [
            'ffmpeg',
            '-ss', str(start),
            '-i', str(video_path),
            '-t', str(duration),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(audio_path)
        ]
        
        logger.info(f"Extracting audio segment {start:.1f}s - {end:.1f}s")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not audio_path.exists():
            raise VideoProcessingError(f"Segment audio file was not created: {audio_path}")
        
        return str(audio_path)
    
    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(f"FFmpeg segment audio error: {e.stderr}")
    except Exception as e:
        raise VideoProcessingError(f"Failed to extract segment audio: {str(e)}")


def extract_segment_frames(
    video_path: str,
    start: float,
    end: float,
    output_dir: str,
    interval: int = 5,
    segment_index: int = 0
) -> List[str]:
    """
    Extract frames only within a specific segment time range.
    
    Args:
        video_path: Path to the input video file
        start: Start time in seconds
        end: End time in seconds
        output_dir: Directory to save extracted frames
        interval: Extract 1 frame every N seconds (default: 5)
        segment_index: Segment index for frame naming
    
    Returns:
        List of paths to extracted frame images
    
    Raises:
        VideoProcessingError: If frame extraction fails
    """
    frame_paths = []
    
    try:
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            raise VideoProcessingError(f"Failed to open video file: {video_path}")
        
        fps = video.get(cv2.CAP_PROP_FPS)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Calculate timestamps within segment
        current_time = start
        frame_count = 0
        
        while current_time < end:
            # Calculate frame number
            frame_number = int(current_time * fps)
            
            # Seek to frame
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = video.read()
            
            if not ret:
                logger.warning(f"Failed to read frame at {current_time}s")
                current_time += interval
                continue
            
            # Save frame with segment and time info
            frame_filename = f"seg{segment_index:02d}_frame_{frame_count:04d}_t{current_time:.1f}s.jpg"
            frame_path = output_path / frame_filename
            
            cv2.imwrite(str(frame_path), frame)
            frame_paths.append(str(frame_path))
            
            frame_count += 1
            current_time += interval
        
        video.release()
        
        logger.info(f"Extracted {len(frame_paths)} frames from segment {segment_index} ({start:.1f}s - {end:.1f}s)")
        
        return frame_paths
    
    except cv2.error as e:
        raise VideoProcessingError(f"OpenCV error during segment extraction: {str(e)}")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error during segment frame extraction: {str(e)}")


def extract_frames_at_times(
    video_path: str,
    output_dir: str,
    timestamps: List[float]
) -> List[str]:
    """
    Extract frames at specific timestamps (alias/wrapper for extract_frames_at_timestamps).
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save frames
        timestamps: List of timestamps in seconds
    
    Returns:
        List of frame file paths
    """
    return extract_frames_at_timestamps(video_path, output_dir, timestamps)


