"""
DevLens Agent Orchestrator

Single orchestrator that coordinates all tools for video documentation generation.
Replaces scattered orchestration logic in routes.py with a clean, testable interface.
"""

import logging
from pathlib import Path
from typing import Optional, Callable, Awaitable

from pydantic import BaseModel

from app.services.session_manager import get_session_manager, SessionManager
from app.services.video_pipeline import (
    process_video_pipeline,
    process_video_pipeline_segmented,
    VideoPipelineResult,
    PipelineError,
    extract_frames_uniform,
    transcribe_audio,
    detect_scene_boundaries_with_flash
)
from app.services.video_processor import create_low_fps_proxy, extract_frames_at_timestamps
from app.services.video_processor import get_video_duration
from app.services.ai_generator import get_generator
from app.services.prompt_loader import get_prompt_loader, PromptLoadError
from app.core.observability import record_event, EventType

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Options Model
# =============================================================================

class DevLensAgentOptions(BaseModel):
    """Options for documentation generation"""
    mode: str = "general_doc"
    language: str = "en"
    project_name: Optional[str] = None
    use_segmented_pipeline: bool = False
    segment_duration_sec: int = 30
    stt_provider: str = "auto"


class DevLensResult(BaseModel):
    """Result from documentation generation"""
    session_id: str
    status: str
    documentation: str
    mode: str
    mode_name: str
    project_name: str
    stt_provider: Optional[str] = "unknown"
    transcript: Optional[str] = None
    transcript_segments: Optional[list] = None
    frames_count: Optional[int] = None
    
    model_config = {"arbitrary_types_allowed": True}




# =============================================================================
# DevLens Agent
# =============================================================================

class DevLensAgent:
    """
    Single orchestrator for video documentation generation.
    
    Coordinates:
    - SessionManager: session lifecycle and state
    - VideoPipeline: video processing (frames, audio, AI generation)
    """
    
    def __init__(
        self,
        session_manager: Optional[SessionManager] = None
    ):
        """
        Initialize the DevLens Agent.
        
        Args:
            session_manager: SessionManager instance (defaults to singleton)
        """
        self._session_manager = session_manager
    
    @property
    def session_manager(self) -> SessionManager:
        """Get or create SessionManager"""
        if self._session_manager is None:
            self._session_manager = get_session_manager()
        return self._session_manager
    
    async def generate_documentation(
        self,
        session_id: str,
        video_path: Path,
        options: DevLensAgentOptions,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
    ) -> DevLensResult:
        """
        Generate documentation from a video file.
        
        This is the main orchestration method that:
        1. Loads prompt configuration
        2. Starts session processing
        3. Runs video pipeline
        4. Returns result
        
        Args:
            session_id: Unique session identifier
            video_path: Path to the video file
            options: Generation options (mode, language, etc.)
            progress_callback: Optional async callback for progress updates
        
        Returns:
            DevLensResult with generated documentation
        
        Raises:
            PipelineError: If video processing fails
            PromptLoadError: If prompt configuration cannot be loaded
        """
        project_name = options.project_name or "Untitled Project"
        
        # Record event
        record_event(session_id, EventType.STATUS_CHANGED, {
            "new_status": "agent_processing",
            "mode": options.mode
        })
        
        try:
            # Re-route to new orchestration map
            config = {
                "mode": options.mode,
                "project_name": project_name,
                "stt_provider": options.stt_provider,
                "use_segmented_pipeline": options.use_segmented_pipeline,
                "segment_duration_sec": options.segment_duration_sec
            }
            
            return await self.process_video(session_id, str(video_path), config)
        
        except Exception as e:
            logger.error(f"[Agent] Unexpected error: {e}")
            self.session_manager.fail(session_id, str(e))
            raise PipelineError(f"Agent error: {str(e)}")

    async def process_video(self, session_id: str, video_path: str, config: dict):
        """
        Orchestrate video processing based on mode.
        """
        mode = config.get("mode", "scene_detection")
        
        logger.info(f"[Agent] Processing session {session_id} with mode: {mode}")
        
        if mode == "viral_clip_gen":
            return await self._process_viral_clips(session_id, video_path, config)
        
        elif mode == "scene_detection":
            return await self._process_scene_cataloging(session_id, video_path, config)
        
        elif mode == "subtitle_extractor":
            return await self._process_subtitles(session_id, video_path, config)
        
        elif mode == "character_tracker":
            return await self._process_character_tracking(session_id, video_path, config)
        
        else:
            return await self._process_standard(session_id, video_path, config)


    async def _process_scene_cataloging(
        self,
        session_id: str,
        video_path: str,
        config: dict
    ) -> DevLensResult:
        """
        Scene Detection Mode with Dual-Stream Optimization (DevLens pattern).
        
        Flow:
        1. Create 1fps proxy (fast, small)
        2. Flash analyzes proxy → finds scene boundaries
        3. Extract hi-res frames only at boundaries
        4. Pro generates detailed catalog
        """
        logger.info("[Agent] 🎬 Starting Dual-Stream Scene Detection...")
        
        try:
            # Get video info
            duration = get_video_duration(str(video_path))
            logger.info(f"[Agent] Video: {duration:.1f}s")
            
            # Step 1: Transcription (for context)
            logger.info("[Agent] 🎤 Step 1: Transcribing audio...")
            transcription_result = await transcribe_audio(
                session_id,
                Path(video_path),
                stt_provider=config.get("stt_provider", "auto")
            )
            transcription_text = transcription_result.get("full_text", "")
            
            # Step 2: Create 1fps proxy
            logger.info("[Agent] 📹 Step 2: Creating 1fps proxy...")
            # Use run_in_threadpool for ffmpeg
            from fastapi.concurrency import run_in_threadpool
            proxy_path = await run_in_threadpool(create_low_fps_proxy, str(video_path), None, 1)
            
            # Step 3: Detect scene boundaries with Flash
            logger.info("[Agent] ⚡ Step 3: Detecting scenes with Gemini Flash...")
            boundaries = await detect_scene_boundaries_with_flash(
                proxy_video_path=proxy_path,
                transcription=transcription_text,
                context_keywords=config.get("keywords", [])
            )
            
            logger.info(f"[Agent] Found {len(boundaries)} scene boundaries")
            
            # Step 4: Extract hi-res frames at boundaries
            logger.info("[Agent] 🎨 Step 4: Extracting hi-res frames...")
            timestamps = [b["time_sec"] for b in boundaries]
            frames_dir = Path(video_path).parent / "frames"
            
            if timestamps:
                 frames = await run_in_threadpool(
                    extract_frames_at_timestamps,
                    str(video_path),
                    str(frames_dir),
                    timestamps
                )
            else:
                logger.warning("[Agent] No scenes detected by Flash, falling back to uniform sampling")
                frame_interval = max(3, duration / 30)
                frames = await run_in_threadpool(
                    extract_frames_uniform,
                    str(video_path),
                    str(frames_dir),
                    frame_interval
                )
            
            logger.info(f"[Agent] Extracted {len(frames)} hi-res frames")
            
            # Step 5: Generate detailed catalog with Pro
            logger.info("[Agent] 🤖 Step 5: Generating scene catalog with Gemini Pro...")
            
            # Get prompts
            prompt_loader = get_prompt_loader()
            prompt_mode = prompt_loader.load_prompt("scene_detection")
            
            system_prompt = prompt_mode.system_instruction
            user_prompt_template = prompt_mode.user_prompt or ""
            
            # Build user prompt with context
            user_prompt = user_prompt_template.format(
                project_name=config.get("project_name", "Untitled"),
                num_frames=len(frames),
                duration_seconds=round(duration, 2),
                transcription=transcription_text,
                session_id=session_id  # Add session_id for frame_path generation
            )
            
            # Generate documentation
            generator = get_generator()
            documentation = await run_in_threadpool(
                generator.generate_documentation,
                frame_paths=frames,
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                model_name="pro",
                session_id=session_id
            )
            
            logger.info(f"[Agent] ✅ Complete! {len(documentation)} chars of documentation")
            
            # Calculate savings
            naive_frames = int(duration / 5)  # Naive: 1 frame per 5 seconds
            savings_pct = ((naive_frames - len(frames)) / naive_frames) * 100 if naive_frames > 0 else 0
            
            return DevLensResult(
                session_id=session_id,
                status="completed",
                documentation=documentation,
                mode="scene_detection",
                mode_name=prompt_mode.name,
                project_name=config.get("project_name", "Untitled"),
                transcript=transcription_text,
                transcript_segments=transcription_result.get("segments"),
                frames_count=len(frames)
            )
            
        except Exception as e:
            logger.error(f"[Agent] ❌ Pipeline error: {e}")
            self.session_manager.fail(session_id, str(e))
            raise PipelineError(str(e))


    async def _process_viral_clips(self, session_id: str, video_path: str, config: dict):
        """Viral Clip Mode: Find shareable moments. Uses standard pipeline."""
        logger.info("[Agent] 🔥 Starting Viral Clips Pipeline...")
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("viral_clip_gen")
        
        result = await process_video_pipeline(
            video_path=Path(video_path),
            task_id=session_id,
            prompt_config=prompt_config,
            project_name=config.get("project_name", "Viral Clips"),
            context_keywords=["hooks", "viral", "funny", "insightful"],
            mode="viral_clip_gen"
        )
        return self._pipeline_result_to_devlens_result(result, session_id)


    async def _process_subtitles(self, session_id: str, video_path: str, config: dict):
        """SUBTITLES: Just STT"""
        logger.info("[Agent] 📜 Starting Subtitle Pipeline...")
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt("subtitle_extractor")
        
        result = await process_video_pipeline(
            video_path=Path(video_path),
            task_id=session_id,
            prompt_config=prompt_config,
            project_name=config.get("project_name", "Subtitles"),
            mode="subtitle_extractor"
        )
        return self._pipeline_result_to_devlens_result(result, session_id)


    async def _process_character_tracking(self, session_id: str, video_path: str, config: dict):
        """CHARACTER TRACKING: Visual + temporal analysis"""
        return await self._process_standard(session_id, video_path, config)


    async def _process_standard(self, session_id: str, video_path: str, config: dict):
        """Fall back to standard pipeline"""
        mode = config.get("mode", "general_doc")
        logger.info(f"[Agent] Starting Standard Pipeline ({mode})...")
        
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt(mode)
        
        result = await process_video_pipeline(
            video_path=Path(video_path),
            task_id=session_id,
            prompt_config=prompt_config,
            project_name=config.get("project_name", "Untitled"),
            mode=mode,
            stt_provider=config.get("stt_provider", "auto")
        )
        return self._pipeline_result_to_devlens_result(result, session_id)

    def _pipeline_result_to_devlens_result(self, result: VideoPipelineResult, session_id: str) -> DevLensResult:
        return DevLensResult(
            session_id=session_id,
            status=result.status,
            documentation=result.documentation,
            mode=result.mode,
            mode_name=result.mode_name,
            project_name=result.project_name,
            stt_provider=result.stt_provider,
            transcript=result.transcript,
            transcript_segments=result.transcript_segments
        )

_devlens_agent: Optional[DevLensAgent] = None


def get_devlens_agent() -> DevLensAgent:
    """Get or create the DevLens Agent singleton"""
    global _devlens_agent
    if _devlens_agent is None:
        _devlens_agent = DevLensAgent()
    return _devlens_agent


def reset_devlens_agent() -> None:
    """Reset the singleton (for testing)"""
    global _devlens_agent
    _devlens_agent = None
