"""
Shared video processing pipeline service for DevLens AI.

This module consolidates the video processing logic used across multiple routes
to eliminate code duplication (CR_FINDINGS 3.1).
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Awaitable
from typing import Optional, List, Dict, Any, Callable, Awaitable
import logging
import time

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.video_processor import (
    extract_frames,
    get_video_duration,
    VideoProcessingError,
    split_into_segments,
    extract_segment_frames,
    create_low_fps_proxy
)
from app.services.clip_generator import ClipGenerator
import json
import re

from app.services.ai_generator import get_generator, AIGenerationError
from app.services.prompt_loader import PromptConfig
from app.services.storage_service import get_storage_service
from app.core.observability import get_acontext_client, extract_code_blocks, record_event, EventType

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
        
        # Record video upload event
        record_event(task_id, EventType.VIDEO_UPLOADED, {
            "filename": video_path.name,
            "duration_sec": round(duration, 2)
        })
    except VideoProcessingError as e:
        raise PipelineError(f"Invalid video file: {str(e)}")
    
    
    # 2 & 3. Optimization: Create Low-FPS Proxy for Semantic Analysis
    if progress_callback:
        await progress_callback(10, "Analyzing video duration...")

    generator = get_generator()
    relevant_segments = None
    
    try:
        logger.info("Starting Dual-Stream Optimization: Creating Low-FPS Proxy...")
        
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
    
    # 3.5 Optional: Hebrish STT Transcription
    transcript_text = ""
    srt_subtitles = ""
    try:
        from app.services.stt_hebrish_service import get_hebrish_stt_service
        from app.services.video_processor import extract_audio
        
        should_run_stt = settings.hebrish_stt_enabled or mode == "subtitle_extractor"
        
        if should_run_stt:
            if progress_callback:
                await progress_callback(40, "Transcribing audio (Hebrish)...")
                
            logger.info("Starting Hebrish STT transcription...")
            start_time = time.time()
            
            # Extract audio first
            audio_path = await run_in_threadpool(extract_audio, str(video_path))
            
            # Transcribe
            stt_service = get_hebrish_stt_service()
            if stt_service.is_available:
                stt_result = await run_in_threadpool(stt_service.transcribe, audio_path)
                
                # Format results
                transcript_text = "\n".join([s["text"] for s in stt_result.segments])
                
                # Generate SRT
                # Quick helper for SRT formatting
                def format_srt_time(seconds):
                    millis = int((seconds % 1) * 1000)
                    seconds = int(seconds)
                    minutes = seconds // 60
                    hours = minutes // 60
                    minutes %= 60
                    seconds %= 60
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

                srt_lines = []
                for i, seg in enumerate(stt_result.segments, 1):
                    srt_lines.append(f"{i}")
                    srt_lines.append(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}")
                    srt_lines.append(f"{seg['text']}\n")
                
                srt_subtitles = "\n".join(srt_lines)
                
                logger.info(f"STT complete. Duration: {time.time() - start_time:.2f}s")
                
                # If mode is subtitle_extractor, we might short-circuit here or pass it to generation
            else:
                logger.warning("Hebrish STT service requested but model unavailable")
                
    except Exception as e:
        logger.error(f"STT processing failed: {e}")
        # Continue pipeline without STT

    
    # 4. Frame extraction (Smart Extraction from Original High-Qual Video)
    if progress_callback:
        await progress_callback(50, "Extracting key frames...")

    frames_dir = task_dir / "frames"
    try:
        timestamps = []
        if relevant_segments:
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
        else:
             timestamps = None # Use None to indicate regular sampling if no smart segments found

        # Extract from ORIGINAL high-quality video
        frame_paths = await run_in_threadpool(
            extract_frames,
            str(video_path),
            str(frames_dir),
            settings.frame_interval,
            timestamps
        )
        logger.info(f"Extracted {len(frame_paths)} high-quality frames")
        
        # Record frames sampled event
        record_event(task_id, EventType.FRAMES_SAMPLED, {
            "count": len(frame_paths),
            "mode": "smart" if timestamps else "regular"
        })
    except VideoProcessingError as e:
        raise PipelineError(f"Frame extraction failed: {str(e)}")
    
    # 5. Generate documentation
    try:
        if progress_callback:
            await progress_callback(70, "Generating documentation with Gemini...")
        
        # Record doc generation start
        record_event(task_id, EventType.DOC_GENERATION_STARTED, {
            "frame_count": len(frame_paths),
            "project_name": project_name
        })
        
        if mode == "subtitle_extractor" and srt_subtitles:
             # Short-circuit for subtitle mode if we have result
             documentation = srt_subtitles
             logger.info(f"Generated subtitles for task {task_id}")
        else:
            # Wrapped in run_in_threadpool to prevent blocking the event loop (CR_FINDINGS 1.1)
            documentation = await run_in_threadpool(
                generator.generate_documentation,
                frame_paths,
                prompt_config,
                transcript_text,  # Pass STT transcript as context
                project_name
            )
            logger.info(f"Generated documentation for task {task_id}")
        
        # 5.5 Post-Processing for Clip Generator
        if mode == "clip_generator":
            try:
                # Extract JSON from potential markdown blocks
                json_str = documentation
                json_match = re.search(r'```json\s*(.*?)\s*```', documentation, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                
                clips_data = json.loads(json_str)
                if isinstance(clips_data, list):
                    logger.info(f"Generating {len(clips_data)} viral clips...")
                    clip_gen = ClipGenerator(output_dir=str(task_dir / "clips"))
                    
                    generated_clips_info = []
                    for i, clip in enumerate(clips_data):
                        try:
                            # Parse timestamps (flexible handling)
                            start = float(clip.get("start_time", clip.get("start", 0)))
                            end = float(clip.get("end_time", clip.get("end", 0)))
                            
                            clip_path = await run_in_threadpool(
                                clip_gen.create_clip,
                                str(video_path),
                                start,
                                end,
                                "vertical" # Default to vertical for social
                            )
                            
                            generated_clips_info.append(f"- **Clip {i+1}**: {clip.get('hook', 'Viral Clip')} ([View]({Path(clip_path).name}))")
                            clip['file_path'] = str(clip_path) # Update data with path
                            
                        except Exception as e:
                            logger.error(f"Failed to generate clip {i}: {e}")
                            generated_clips_info.append(f"- **Clip {i+1}**: Failed ({str(e)})")
                    
                    # Append generation report to documentation
                    documentation += "\n\n## Generated Clips\n" + "\n".join(generated_clips_info)
                    
            except json.JSONDecodeError:
                logger.warning("Failed to parse Clip Generator output as JSON")
            except Exception as e:
                logger.error(f"Error in clip generation post-processing: {e}")

        # Record doc generation complete in both cases
        record_event(task_id, EventType.DOC_GENERATION_COMPLETED, {
            "doc_length": len(documentation)
        })
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


async def process_video_pipeline_segmented(
    video_path: Path,
    task_id: str,
    prompt_config: PromptConfig,
    project_name: str,
    segment_duration_sec: int = 30,
    mode: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
) -> VideoPipelineResult:
    """
    Segmented video processing pipeline - processes video in chunks.
    
    Similar to realtime voice agent audio chunks, this processes the video
    in logical segments for:
    - More granular progress reporting
    - Smaller AI context windows per segment
    - Potential for streaming/incremental output
    
    Args:
        video_path: Path to the video file
        task_id: Unique task/session identifier
        prompt_config: Loaded prompt configuration
        project_name: Name of the project being documented
        segment_duration_sec: Duration of each segment in seconds (default: 30)
        mode: Documentation mode string (for storage)
        progress_callback: Optional async callback for progress updates
    
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
        
        # Record video upload event
        record_event(task_id, EventType.VIDEO_UPLOADED, {
            "filename": video_path.name,
            "duration_sec": round(duration, 2),
            "mode": "segmented"
        })
    except VideoProcessingError as e:
        raise PipelineError(f"Invalid video file: {str(e)}")
    
    if progress_callback:
        await progress_callback(5, "Analyzing video structure...")
    
    # 2. Split into segments
    try:
        segments = await run_in_threadpool(
            split_into_segments,
            str(video_path),
            segment_duration_sec
        )
        logger.info(f"Split video into {len(segments)} segments")
        
        # Record segment creation event
        record_event(task_id, EventType.SEGMENT_CREATED, {
            "segment_count": len(segments),
            "segment_duration_sec": segment_duration_sec
        })
    except VideoProcessingError as e:
        raise PipelineError(f"Failed to split video: {str(e)}")
    
    if progress_callback:
        await progress_callback(10, f"Processing {len(segments)} segments...")
    
    # 3. Process each segment
    generator = get_generator()
    segment_docs = []
    frames_dir = task_dir / "frames"
    
    # Progress allocation: 10-85% for segment processing
    progress_per_segment = 75 / max(len(segments), 1)
    
    for seg in segments:
        seg_index = seg["index"]
        seg_start = seg["start"]
        seg_end = seg["end"]
        
        # Update progress for this segment
        current_progress = 10 + int(progress_per_segment * seg_index)
        if progress_callback:
            await progress_callback(
                current_progress,
                f"Processing segment {seg_index + 1}/{len(segments)} ({seg_start:.0f}s - {seg_end:.0f}s)"
            )
        
        # 3a. Extract frames for this segment
        try:
            segment_frames_dir = frames_dir / f"seg_{seg_index:02d}"
            frame_paths = await run_in_threadpool(
                extract_segment_frames,
                str(video_path),
                seg_start,
                seg_end,
                str(segment_frames_dir),
                settings.frame_interval,
                seg_index
            )
            logger.info(f"Segment {seg_index}: extracted {len(frame_paths)} frames")
        except VideoProcessingError as e:
            logger.warning(f"Segment {seg_index} frame extraction failed: {e}")
            frame_paths = []
        
        # 3b. Generate documentation for this segment
        if frame_paths:
            try:
                segment_doc = await run_in_threadpool(
                    generator.generate_segment_doc,
                    seg,
                    frame_paths,
                    prompt_config,
                    project_name,
                    None  # audio_summary - future enhancement
                )
            except AIGenerationError as e:
                logger.warning(f"Segment {seg_index} doc generation failed: {e}")
                segment_doc = f"*Segment {seg_index + 1} processing failed.*\n"
        else:
            segment_doc = f"*No frames extracted for segment {seg_index + 1}.*\n"
        
        segment_docs.append({
            "index": seg_index,
            "start": seg_start,
            "end": seg_end,
            "doc": segment_doc
        })
        
        # Record segment processed event
        record_event(task_id, EventType.SEGMENT_PROCESSED, {
            "segment_index": seg_index,
            "frame_count": len(frame_paths),
            "doc_length": len(segment_doc)
        })
    
    # 4. Merge segments
    if progress_callback:
        await progress_callback(85, "Merging segment documentation...")
    
    try:
        documentation = generator.merge_segments(segment_docs, project_name)
        logger.info(f"Merged {len(segment_docs)} segments into final document")
    except Exception as e:
        raise PipelineError(f"Failed to merge segments: {str(e)}")
    
    # 5. Store artifacts
    if progress_callback:
        await progress_callback(90, "Storing artifacts...")
    
    _store_artifacts(task_id, documentation, project_name)
    
    # 6. Persist to history
    storage = get_storage_service()
    selected_mode = mode or "general_doc"
    storage.add_session(task_id, {
        "title": project_name,
        "topic": prompt_config.name,
        "status": "completed",
        "documentation": documentation,
        "mode": selected_mode,
        "mode_name": prompt_config.name,
        "segments_processed": len(segments)
    })
    
    if progress_callback:
        await progress_callback(100, "Complete!")
    
    return VideoPipelineResult(
        task_id=task_id,
        documentation=documentation,
        status="completed",
        mode=selected_mode,
        mode_name=prompt_config.name,
        project_name=project_name
    )

