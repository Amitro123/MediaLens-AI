"""
Shared video processing pipeline service for DevLens AI.

This module consolidates the video processing logic used across multiple routes
to eliminate code duplication (CR_FINDINGS 3.1).
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Awaitable
import logging

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.video_processor import extract_frames, get_video_duration, VideoProcessingError
from app.services.ai_generator import get_generator, AIGenerationError
from app.services.prompt_loader import PromptConfig
from app.services.storage_service import get_storage_service
from app.core.observability import get_acontext_client, extract_code_blocks

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Custom exception for pipeline processing errors."""
    pass


class VideoPipelineResult:
    """Container for video processing pipeline results."""
    
    def __init__(
        self,
        task_id: str,
        documentation: str,
        status: str = "completed",
        mode: str = "general_doc",
        mode_name: str = "Technical Documentation",
        project_name: str = "Untitled Project"
    ):
        self.task_id = task_id
        self.documentation = documentation
        self.status = status
        self.mode = mode
        self.mode_name = mode_name
        self.project_name = project_name


async def process_video_pipeline(
    video_path: Path,
    task_id: str,
    prompt_config: PromptConfig,
    project_name: str,
    context_keywords: Optional[List[str]] = None,
    mode: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
) -> VideoPipelineResult:
    """
    Core video processing pipeline shared across upload routes.
    
    This function consolidates the common processing steps:
    1. Validate video duration
    2. Extract audio (optional, for smart frame selection)
    3. Analyze audio relevance (if context_keywords provided)
    4. Extract frames (smart or regular)
    5. Generate documentation via AI
    6. Store artifacts
    7. Persist to history
    
    Args:
        video_path: Path to the video file
        task_id: Unique task/session identifier
        prompt_config: Loaded prompt configuration
        project_name: Name of the project being documented
        context_keywords: Optional keywords for smart frame extraction
        mode: Documentation mode string (for storage)
    
    Returns:
        VideoPipelineResult with generated documentation
    
    Raises:
        PipelineError: If any step in the pipeline fails
    """
    task_dir = video_path.parent
    
    # 1. Validate video duration
    try:
        duration = await run_in_threadpool(get_video_duration, str(video_path))
        if duration > settings.max_video_length:
            raise PipelineError(
                f"Video too long. Maximum: {settings.max_video_length}s "
                f"({settings.max_video_length // 60} minutes)"
            )
        logger.info(f"Video duration: {duration:.2f}s")
    except VideoProcessingError as e:
        raise PipelineError(f"Invalid video file: {str(e)}")
    
    
    # 2 & 3. Optimization: Create Low-FPS Proxy for Semantic Analysis
    if progress_callback:
        await progress_callback(10, "Analyzing video duration...")

    generator = get_generator()
    relevant_segments = None
    
    try:
        logger.info("Starting Dual-Stream Optimization: Creating Low-FPS Proxy...")
        from app.services.video_processor import create_low_fps_proxy
        
        if progress_callback:
            await progress_callback(20, "Creating optimized proxy...")

        # 1 FPS Proxy for analysis
        proxy_path = await run_in_threadpool(create_low_fps_proxy, str(video_path))
        
        if progress_callback:
            await progress_callback(30, "Analyzing content relevance...")

        logger.info("Starting Multimodal Semantic Analysis using Gemini Flash...")
        # Use multimodal analysis on the proxy video instead of audio-only
        # Wrapped in run_in_threadpool to prevent blocking the event loop (CR_FINDINGS 1.1)
        relevant_segments = await run_in_threadpool(
            generator.analyze_video_relevance,
            proxy_path,
            context_keywords=context_keywords
        )
    except Exception as e:
        logger.warning(f"Semantic analysis failed, falling back to regular sampling: {e}")
        relevant_segments = None
    
    # 4. Frame extraction (Smart Extraction from Original High-Qual Video)
    if progress_callback:
        await progress_callback(50, "Extracting key frames...")

    frames_dir = task_dir / "frames"
    try:
        timestamps = None
        if relevant_segments:
            timestamps = []
            for seg in relevant_segments:
                # Add key timestamps precisely selected by Gemini Flash
                if 'key_timestamps' in seg:
                    timestamps.extend(seg['key_timestamps'])
                else:
                    # Fallback to start/mid/end if key_timestamps missing
                    timestamps.append(seg['start'])
                    if seg['end'] - seg['start'] > 5.0:
                        timestamps.append((seg['start'] + seg['end']) / 2)
                    timestamps.append(seg['end'])
            
            # Deduplicate and sort timestamps
            timestamps = sorted(list(set(timestamps)))
            logger.info(f"Smart Sampling: Extracting {len(timestamps)} high-res frames at specific timestamps")
        
        # Extract from ORIGINAL high-quality video
        frame_paths = await run_in_threadpool(
            extract_frames,
            str(video_path),
            str(frames_dir),
            settings.frame_interval,
            timestamps
        )
        logger.info(f"Extracted {len(frame_paths)} high-quality frames")
    except VideoProcessingError as e:
        raise PipelineError(f"Frame extraction failed: {str(e)}")
    
    # 5. Generate documentation
    try:
        if progress_callback:
            await progress_callback(70, "Generating documentation with Gemini...")
        
        # Wrapped in run_in_threadpool to prevent blocking the event loop (CR_FINDINGS 1.1)
        documentation = await run_in_threadpool(
            generator.generate_documentation,
            frame_paths,
            prompt_config,
            "",  # RAG context (future enhancement)
            project_name
        )
        logger.info(f"Generated documentation for task {task_id}")
    except AIGenerationError as e:
        raise PipelineError(f"AI generation failed: {str(e)}")
    
    # 6. Store artifacts in Acontext (Flight Recorder)
    _store_artifacts(task_id, documentation, project_name)
    
    # 7. Persist to history
    storage = get_storage_service()
    selected_mode = mode or "general_doc"
    storage.add_session(task_id, {
        "title": project_name,
        "topic": prompt_config.name,
        "status": "completed",
        "documentation": documentation,
        "mode": selected_mode,
        "mode_name": prompt_config.name
    })
    
    return VideoPipelineResult(
        task_id=task_id,
        documentation=documentation,
        status="completed",
        mode=selected_mode,
        mode_name=prompt_config.name,
        project_name=project_name
    )


def _store_artifacts(task_id: str, documentation: str, project_name: str) -> None:
    """
    Store generated documentation and code blocks as artifacts in Acontext.
    
    Args:
        task_id: Unique task/session identifier
        documentation: Generated markdown documentation
        project_name: Name of the project
    """
    try:
        client = get_acontext_client()
        if not client.is_enabled:
            return
        
        # Store the main documentation
        client.add_artifact(
            filename=f"{task_id}_docs.md",
            content=documentation.encode('utf-8'),
            path="/outputs/"
        )
        logger.info(f"Stored documentation artifact for {task_id}")
        
        # Extract and store code blocks
        code_blocks = extract_code_blocks(documentation)
        for i, block in enumerate(code_blocks):
            ext = block.get('lang', 'txt')
            client.add_artifact(
                filename=f"{task_id}_code_{i}.{ext}",
                content=block['code'].encode('utf-8'),
                path="/outputs/code/"
            )
        
        if code_blocks:
            logger.info(f"Stored {len(code_blocks)} code block artifacts for {task_id}")
            
    except Exception as e:
        # Don't fail the request if artifact storage fails
        logger.warning(f"Failed to store artifacts in Acontext: {e}")
