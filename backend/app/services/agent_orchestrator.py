"""
DevLens Agent Orchestrator

Single orchestrator that coordinates all tools for video documentation generation.
Replaces scattered orchestration logic in routes.py with a clean, testable interface.
"""

import logging
from pathlib import Path
from typing import Optional, Callable, Awaitable, Any

from pydantic import BaseModel

from app.services.session_manager import get_session_manager, SessionManager
from app.services.video_pipeline import (
    process_video_pipeline,
    process_video_pipeline_segmented,
    VideoPipelineResult,
    PipelineError
)
from app.services.prompt_loader import get_prompt_loader, PromptLoadError
from app.services.calendar_service import get_calendar_watcher, CalendarWatcher
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
    calendar_event_id: Optional[str] = None
    use_segmented_pipeline: bool = False
    segment_duration_sec: int = 30


class DevLensResult(BaseModel):
    """Result from documentation generation"""
    session_id: str
    status: str
    documentation: str
    mode: str
    mode_name: str
    project_name: str
    
    
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
    - CalendarService: optional meeting context enrichment
    
    Example:
        agent = get_devlens_agent()
        result = await agent.generate_documentation(
            session_id="abc123",
            video_path=Path("/path/to/video.mp4"),
            options=DevLensAgentOptions(mode="bug_report")
        )
    """
    
    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        calendar: Optional[CalendarWatcher] = None
    ):
        """
        Initialize the DevLens Agent.
        
        Args:
            session_manager: SessionManager instance (defaults to singleton)
            calendar: CalendarWatcher instance (defaults to singleton)
        """
        self._session_manager = session_manager
        self._calendar = calendar
    
    @property
    def session_manager(self) -> SessionManager:
        """Get or create SessionManager"""
        if self._session_manager is None:
            self._session_manager = get_session_manager()
        return self._session_manager
    
    @property
    def calendar(self) -> Optional[CalendarWatcher]:
        """Get or create CalendarWatcher"""
        if self._calendar is None:
            try:
                self._calendar = get_calendar_watcher()
            except Exception:
                self._calendar = None
        return self._calendar
    
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
        3. Enriches context from calendar (if available)
        4. Runs video pipeline
        5. Returns result
        
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
            # 1. Load prompt configuration
            prompt_loader = get_prompt_loader()
            prompt_config = prompt_loader.load_prompt(options.mode)
            logger.info(f"[Agent] Loaded prompt mode: {options.mode} - {prompt_config.name}")
            
            # 2. Enrich context from calendar if event_id provided
            context_keywords = None
            if options.calendar_event_id and self.calendar:
                try:
                    session = self.calendar.get_session(options.calendar_event_id)
                    if session and hasattr(session, 'context_keywords'):
                        context_keywords = session.context_keywords
                        logger.info(f"[Agent] Enriched with calendar context: {context_keywords}")
                except Exception as e:
                    logger.warning(f"[Agent] Failed to get calendar context: {e}")
            
            # 3. Run video pipeline
            if options.use_segmented_pipeline:
                logger.info(f"[Agent] Using segmented pipeline ({options.segment_duration_sec}s segments)")
                result = await process_video_pipeline_segmented(
                    video_path=video_path,
                    task_id=session_id,
                    prompt_config=prompt_config,
                    project_name=project_name,
                    segment_duration_sec=options.segment_duration_sec,
                    mode=options.mode,
                    progress_callback=progress_callback
                )
            else:
                logger.info("[Agent] Using standard pipeline")
                result = await process_video_pipeline(
                    video_path=video_path,
                    task_id=session_id,
                    prompt_config=prompt_config,
                    project_name=project_name,
                    context_keywords=context_keywords,
                    mode=options.mode,
                    progress_callback=progress_callback
                )
            
            # 4. Return result
            logger.info(f"[Agent] Documentation generated for session {session_id}")
            
            return DevLensResult(
                session_id=session_id,
                status=result.status,
                documentation=result.documentation,
                mode=result.mode,
                mode_name=result.mode_name,
                project_name=result.project_name
            )
        
        except PromptLoadError as e:
            logger.error(f"[Agent] Prompt load error: {e}")
            self.session_manager.fail(session_id, str(e))
            raise
        
        except PipelineError as e:
            logger.error(f"[Agent] Pipeline error: {e}")
            self.session_manager.fail(session_id, str(e))
            raise
        
        except Exception as e:
            logger.error(f"[Agent] Unexpected error: {e}")
            self.session_manager.fail(session_id, str(e))
            raise PipelineError(f"Agent error: {str(e)}")


# =============================================================================
# Singleton
# =============================================================================

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
