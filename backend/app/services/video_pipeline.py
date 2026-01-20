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
    create_low_fps_proxy,
    extract_audio
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
        project_name: str = "Untitled Project",
        stt_provider: str = "unknown",
        transcript: Optional[str] = None,
        transcript_segments: Optional[List[Dict[str, Any]]] = None
    ):
        self.task_id = task_id
        self.documentation = documentation
        self.status = status
        self.mode = mode
        self.mode_name = mode_name
        self.project_name = project_name
        self.stt_provider = stt_provider
        self.transcript = transcript
        self.transcript_segments = transcript_segments


async def process_video_pipeline(
    video_path: Path,
    task_id: str,
    prompt_config: PromptConfig,
    project_name: str,
    context_keywords: Optional[List[str]] = None,
    mode: Optional[str] = None,
    stt_provider: str = "auto",
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
        logger.warning("="*80)
        logger.warning("⚠️  [Gemini] Semantic analysis FAILED")
        logger.warning(f"⚠️  Error type: {type(e).__name__}")
        logger.warning(f"⚠️  Error message: {str(e)}")
        
        # Check if it's API key error:
        error_str = str(e)
        if "API key not valid" in error_str or "dummy_key" in str(settings.gemini_api_key):
            logger.warning("⚠️  Gemini API key is invalid or dummy key detected")
            logger.warning("⚠️  To use semantic analysis, set a valid GEMINI_API_KEY")
        
        logger.warning("✅ Falling back to regular frame sampling (works without Gemini)")
        logger.warning("="*80)
        relevant_segments = None
    
    # 3.5 Optional: Hebrish STT Transcription
    transcript_text = ""
    srt_subtitles = ""
    stt_provider_used = "unknown"
    try:
        from app.services.stt_hebrish_service import get_hebrish_stt_service
        
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
                # Pass task_id for progress updates and stt_provider
                stt_result = await stt_service.transcribe(audio_path, task_id, stt_provider)
                
                # Determine provider used for metadata
                if "groq" in stt_result.model_used.lower():
                     stt_provider_used = "groq"
                elif "whisper" in stt_result.model_used.lower() or "ivrit-ai" in stt_result.model_used.lower():
                     stt_provider_used = "google" # Maps to 'Accurate' option
                
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
    
    # Prepare session data
    session_data = {
        "title": project_name,
        "topic": prompt_config.name,
        "status": "completed",
        "documentation": documentation,
        "mode": selected_mode,
        "mode_name": prompt_config.name,
        "stt_provider": stt_provider_used,
        "transcript": transcript_text, # Save raw text
    }
    
    # Check if we have segments to save (for interactive transcript)
    if 'stt_service' in locals() and 'stt_result' in locals() and hasattr(stt_result, 'segments'):
         session_data["transcript_segments"] = stt_result.segments

    storage.add_session(task_id, session_data)
    
    return VideoPipelineResult(
        task_id=task_id,
        documentation=documentation,
        status="completed",
        mode=selected_mode,
        mode_name=prompt_config.name,
        project_name=project_name,
        stt_provider=stt_provider_used,
        transcript=transcript_text,
        transcript_segments=stt_result.segments if 'stt_result' in locals() else None
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


def extract_frames_uniform(
    video_path: str,
    output_dir: str,
    interval_seconds: float = 5.0
) -> List[str]:
    """
    Extract frames at uniform intervals (for scene cataloging).
    
    Args:
        video_path: Path to video
        output_dir: Directory to save frames
        interval_seconds: Extract one frame every N seconds
    
    Returns:
        List of frame file paths
    """
    try:
        duration = get_video_duration(video_path)
        num_frames = int(duration / interval_seconds)
        
        logger.info(f"Extracting ~{num_frames} frames (1 per {interval_seconds}s)")
        
        # Calculate exact timestamps
        timestamps = [i * interval_seconds for i in range(num_frames)]
        
        # Use existing extract_frames but with specific timestamps
        frames = extract_frames(
            video_path=video_path,
            output_dir=output_dir,
            timestamps=timestamps
        )
        
        logger.info(f"Extracted {len(frames)} uniform frames")
        
        return frames
        
    except Exception as e:
        logger.error(f"Error extracting uniform frames: {e}")
        raise



async def detect_scene_boundaries_with_flash(
    proxy_video_path: str,
    transcription: str,
    context_keywords: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Use Gemini Flash to analyze proxy and identify scene boundaries.
    
    DevLens pattern: Fast, cheap analysis on 1fps proxy to find key moments.
    
    Returns:
        List of {"time_sec": float, "reason": str, "quality_ok": bool}
    """
    import google.generativeai as genai
    import asyncio
    
    generator = get_generator()
    
    keywords_str = ", ".join(context_keywords) if context_keywords else "general content"
    
    prompt = f"""Analyze this video and identify distinct scenes.

Context keywords: {keywords_str}

Transcription:
{transcription}

Look for:
1. Location/setting changes (indoor → outdoor, different rooms)
2. New people entering or exiting frame
3. Significant action changes
4. Topic shifts in dialogue

VISUAL QUALITY CONTROL:
- NEVER select timestamps showing blank/white screens
- NEVER select loading spinners or blurred transitions
- If a scene boundary happens during loading, shift ±2-3 seconds to find rendered content

Return STRICTLY this JSON format (NO markdown fences):
{{
  "scene_boundaries": [
    {{"time_sec": 0.0, "reason": "Opening scene", "quality_ok": true}},
    {{"time_sec": 15.3, "reason": "Location change to kitchen", "quality_ok": true}}
  ]
}}"""

    try:
        # Upload proxy to Gemini
        logger.info("📤 Uploading proxy to Gemini Flash...")
        video_file = await run_in_threadpool(genai.upload_file, proxy_video_path)
        
        # Wait for processing
        while video_file.state.name == "PROCESSING":
            await asyncio.sleep(1)
            video_file = await run_in_threadpool(genai.get_file, video_file.name)
        
        if video_file.state.name == "FAILED":
            raise Exception(f"Video processing failed: {video_file.state}")
        
        # Analyze with Flash (fast model)
        logger.info("⚡ Analyzing with Gemini Flash...")
        
        # Wrapped in run_in_threadpool
        response = await run_in_threadpool(
            generator.model_flash.generate_content,
            [video_file, prompt],
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        
        # Parse response
        text = response.text.strip()
        if hasattr(generator, 'strip_markdown_fences'):
             text = generator.strip_markdown_fences(text)
             
        result = json.loads(text)
        boundaries = result.get("scene_boundaries", [])
        
        # Filter out low-quality frames
        quality_boundaries = [b for b in boundaries if b.get("quality_ok", True)]
        
        logger.info(f"🎬 Detected {len(quality_boundaries)} quality scene boundaries")
        return quality_boundaries
        
    except Exception as e:
        logger.error(f"Scene boundary detection failed: {e}")
        raise


async def transcribe_audio(
    session_id: str,
    video_path: Path,
    stt_provider: str = "auto"
) -> Dict[str, Any]:
    """
    Transcribe audio from video using Hebrish STT.
    
    Args:
        session_id: Session ID
        video_path: Path to video
        stt_provider: STT provider preference
    
    Returns:
        Dict with "full_text" and "segments"
    """
    from app.services.stt_hebrish_service import get_hebrish_stt_service
    
    
    logger.info(f"🎤 [STT] Provider requested: {stt_provider}")
    logger.info("Starting Hebrish STT transcription...")
    try:
        # Extract audio
        audio_path = await run_in_threadpool(extract_audio, str(video_path))
        
        # Transcribe
        stt_service = get_hebrish_stt_service()
        if stt_service.is_available:
            stt_result = await stt_service.transcribe(audio_path, session_id, stt_provider)
            
            transcript_text = "\n".join([s["text"] for s in stt_result.segments])
            
            return {
                "full_text": transcript_text,
                "segments": stt_result.segments,
                "provider": stt_result.model_used
            }
    except Exception as e:
        logger.error(f"STT processing failed: {e}")
        return {"full_text": "", "segments": []}
    
    return {"full_text": "", "segments": []}

