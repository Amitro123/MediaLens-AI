"""
Centralized SessionManager for pipeline orchestration.

This module provides a single authoritative service for managing all session state
throughout the video processing lifecycle (draft → processing → completed/failed).
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel

from app.services.storage_service import get_storage_service
from app.core.observability import record_event, EventType, get_timeline_path

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Possible states for a processing session"""
    DRAFT = "draft"
    READY = "ready_for_upload"
    DOWNLOADING = "downloading_from_drive"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionState(BaseModel):
    """Internal state model for a session"""
    session_id: str
    status: SessionStatus = SessionStatus.DRAFT
    progress: int = 0
    stage: str = ""
    title: str = "Untitled"
    mode: Optional[str] = None
    mode_name: Optional[str] = None
    error: Optional[str] = None
    result_path: Optional[str] = None
    created_at: datetime
    last_updated: datetime
    metadata: Dict = {}


# Zombie timeout: sessions stuck for >10 minutes are considered stale
STALE_TIMEOUT_SECONDS = 600


class SessionManager:
    """
    Centralized service for managing pipeline session state.
    
    Consolidates state previously spread across:
    - task_results dict (in-memory, volatile)
    - CalendarWatcher.draft_sessions
    - StorageService.history.json
    
    Provides a clean API for:
    - Session lifecycle (create, start, update, complete, fail)
    - Status queries with progress tracking
    - Active session recovery
    - Zombie session cleanup
    """
    
    def __init__(self):
        """Initialize SessionManager with in-memory cache"""
        self._sessions: Dict[str, SessionState] = {}
        self._storage = get_storage_service()
        logger.info("SessionManager initialized")
    
    def create_session(
        self,
        session_id: str,
        metadata: Dict,
        status: SessionStatus = SessionStatus.DRAFT
    ) -> Dict:
        """
        Create a new session (draft or ready for upload).
        
        Args:
            session_id: Unique session identifier
            metadata: dict with title, mode, attendees, etc.
            status: Initial status (default: DRAFT)
        
        Returns:
            Session state dict
        """
        now = datetime.now()
        
        state = SessionState(
            session_id=session_id,
            status=status,
            progress=0,
            stage="created",
            title=metadata.get("title", metadata.get("project_name", "Untitled")),
            mode=metadata.get("mode"),
            mode_name=metadata.get("mode_name"),
            created_at=now,
            last_updated=now,
            metadata=metadata
        )
        
        self._sessions[session_id] = state
        logger.info(f"Created session {session_id} with status {status.value}")
        
        return self._to_dict(state)
    
    def start_processing(self, session_id: str) -> None:
        """
        Mark a session as processing and set initial progress.
        
        Args:
            session_id: Session to start processing
        """
        state = self._get_or_create(session_id)
        state.status = SessionStatus.PROCESSING
        state.progress = 0
        state.stage = "initializing"
        state.last_updated = datetime.now()
        
        # Persist to disk
        self._persist(state)
        
        # Record timeline event
        record_event(session_id, EventType.STATUS_CHANGED, {
            "new_status": "processing",
            "progress": 0
        })
        
        logger.info(f"Session {session_id} started processing")
    
    def update_progress(self, session_id: str, stage: str, progress: int) -> None:
        """
        Update session progress (0-100) and current stage.
        
        Args:
            session_id: Session to update
            stage: Current processing stage (e.g., "extracting_frames", "generating_docs")
            progress: Progress percentage (0-100)
        """
        state = self._get_or_create(session_id)
        state.progress = max(0, min(100, progress))
        state.stage = stage
        state.last_updated = datetime.now()
        
        logger.debug(f"Session {session_id}: {stage} @ {progress}%")
    
    def complete(self, session_id: str, result_path: Optional[str] = None, documentation: Optional[str] = None, stt_provider: Optional[str] = None, transcript: Optional[str] = None, transcript_segments: Optional[List] = None, frames_count: Optional[int] = None) -> None:
        """
        Mark a session as completed and store the result path.
        
        Args:
            session_id: Session to complete
            result_path: Path to the generated documentation file
            documentation: Full documentation content (optional, for persistence)
            stt_provider: The STT provider used (optional)
            transcript: Raw transcript text (optional)
            transcript_segments: List of transcript segments (optional)
        """
        state = self._get_or_create(session_id)
        state.status = SessionStatus.COMPLETED
        state.progress = 100
        state.stage = "completed"
        state.result_path = result_path
        state.last_updated = datetime.now()
        
        if documentation:
            state.metadata["documentation"] = documentation
        
        if stt_provider:
             state.metadata["stt_provider"] = stt_provider

        if transcript:
            state.metadata["transcript"] = transcript
        
        if transcript_segments:
            state.metadata["transcript_segments"] = transcript_segments

        if frames_count is not None:
             state.metadata["frames_count"] = frames_count
        
        # Persist to disk
        self._persist(state, documentation=documentation)
        
        # Record timeline event
        record_event(session_id, EventType.SESSION_COMPLETED, {
            "result_path": result_path
        })
        
        logger.info(f"Session {session_id} completed. Result: {result_path}")
    
    def fail(self, session_id: str, error_message: str) -> None:
        """
        Mark a session as failed with an error message.
        
        Args:
            session_id: Session that failed
            error_message: Description of the failure
        """
        state = self._get_or_create(session_id)
        state.status = SessionStatus.FAILED
        state.error = error_message
        state.stage = "failed"
        state.last_updated = datetime.now()
        
        # Persist to disk
        self._persist(state)
        
        # Record timeline event
        record_event(session_id, EventType.SESSION_FAILED, {
            "error": error_message
        })
        
        logger.error(f"Session {session_id} failed: {error_message}")
    
    def cancel(self, session_id: str) -> bool:
        """
        Cancel an active session.
        
        Args:
            session_id: Session to cancel
            
        Returns:
            True if session was cancelled, False if not found or already completed
        """
        state = self._sessions.get(session_id)
        if not state:
            return False
        
        if state.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
            return False
        
        state.status = SessionStatus.CANCELLED
        state.stage = "cancelled"
        state.last_updated = datetime.now()
        
        self._persist(state)
        
        logger.info(f"Session {session_id} cancelled")
        return True
    
    def get_status(self, session_id: str) -> Optional[Dict]:
        """
        Get session status with progress information.
        
        Args:
            session_id: Session to query
        
        Returns:
            dict with {status, progress, stage, timestamps} or None if not found
        """
        # Check in-memory first
        state = self._sessions.get(session_id)
        
        if state:
            # Check for zombie session
            if self._is_zombie(state):
                self._mark_zombie(state)
            
            return {
                "status": state.status.value,
                "progress": state.progress,
                "stage": state.stage,
                "title": state.title,
                "mode": state.mode,
                "mode_name": state.mode_name,
                "error": state.error,
                "created_at": state.created_at.isoformat(),
                "last_updated": state.last_updated.isoformat()
            }
        
        # Try to load from persistent storage
        persisted = self._storage.get_session_result(session_id)
        if persisted:
            return {
                "status": persisted.get("status", "completed"),
                "progress": 100 if persisted.get("status") == "completed" else 0,
                "stage": "loaded_from_disk",
                "title": persisted.get("project_name", "Untitled"),
                "mode": persisted.get("mode"),
                "mode_name": persisted.get("mode_name"),
                "error": None,
                "created_at": None,
                "last_updated": None
            }
        
        return None
    
    def get_active_session(self) -> Optional[Dict]:
        """
        Get the currently active processing session (if any).
        Used for frontend recovery after page refresh.
        
        Returns:
            Active session info dict or None
        """
        now = datetime.now()
        
        # Check in-memory sessions
        for session_id, state in self._sessions.items():
            if state.status in [SessionStatus.PROCESSING, SessionStatus.DOWNLOADING]:
                # Check for zombie
                if self._is_zombie(state):
                    self._mark_zombie(state)
                    continue
                
                return {
                    "session_id": session_id,
                    "status": state.status.value,
                    "title": state.title,
                    "mode": state.mode,
                    "progress": state.progress
                }
        
        # Check persistent storage for active sessions
        try:
            history = self._storage.get_history()
            for session in history:
                if session.get("status") in ["processing", "uploading", "downloading"]:
                    # Check staleness
                    ts_str = session.get("timestamp")
                    if ts_str:
                        try:
                            session_ts = datetime.fromisoformat(ts_str)
                            if (now - session_ts).total_seconds() > STALE_TIMEOUT_SECONDS:
                                # Mark as failed in storage
                                self._storage.add_session(session.get("id"), {
                                    **session,
                                    "status": "failed",
                                    "error": "Session timed out (Zombie)"
                                })
                                continue
                        except ValueError:
                            pass
                    
                    return {
                        "session_id": session.get("id"),
                        "status": session.get("status"),
                        "title": session.get("title", "Untitled"),
                        "mode": session.get("mode"),
                        "progress": session.get("progress", 0)
                    }
        except Exception as e:
            logger.error(f"Error checking persistent storage for active session: {e}")
        
        return None
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Get full session state object.
        
        Args:
            session_id: Session to retrieve
            
        Returns:
            SessionState or None
        """
        return self._sessions.get(session_id)
    
    def update_metadata(self, session_id: str, metadata: Dict) -> None:
        """
        Update session metadata (e.g., documentation content, mode).
        
        Args:
            session_id: Session to update
            metadata: Metadata dict to merge
        """
        state = self._get_or_create(session_id)
        state.metadata.update(metadata)
        
        if "mode" in metadata:
            state.mode = metadata["mode"]
        if "mode_name" in metadata:
            state.mode_name = metadata["mode_name"]
        if "title" in metadata:
            state.title = metadata["title"]
        
        state.last_updated = datetime.now()
    
    # --- Private helpers ---
    
    def _get_or_create(self, session_id: str) -> SessionState:
        """Get existing session or create a minimal one"""
        if session_id not in self._sessions:
            now = datetime.now()
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                created_at=now,
                last_updated=now
            )
        return self._sessions[session_id]
    
    def _persist(self, state: SessionState, documentation: Optional[str] = None) -> None:
        """Persist session to disk via StorageService"""
        metadata = {
            "title": state.title,
            "topic": state.mode_name or "General",
            "status": state.status.value,
            "mode": state.mode,
            "mode_name": state.mode_name,
            "progress": state.progress,
            "last_updated": state.last_updated.isoformat()
        }
        
        if documentation:
            metadata["documentation"] = documentation
        elif "documentation" in state.metadata:
            metadata["documentation"] = state.metadata["documentation"]

        if "stt_provider" in state.metadata:
            metadata["stt_provider"] = state.metadata["stt_provider"]
        
        if "transcript" in state.metadata:
            metadata["transcript"] = state.metadata["transcript"]
            
        if "transcript_segments" in state.metadata:
            metadata["transcript_segments"] = state.metadata["transcript_segments"]

        if "frames_count" in state.metadata:
            metadata["frames_count"] = state.metadata["frames_count"]
        
        self._storage.add_session(state.session_id, metadata)
    
    def _is_zombie(self, state: SessionState) -> bool:
        """Check if a session is a zombie (stale/stuck)"""
        if state.status not in [SessionStatus.PROCESSING, SessionStatus.DOWNLOADING]:
            return False
        
        elapsed = (datetime.now() - state.last_updated).total_seconds()
        return elapsed > STALE_TIMEOUT_SECONDS
    
    def _mark_zombie(self, state: SessionState) -> None:
        """Mark a zombie session as failed"""
        logger.warning(f"Zombie session detected: {state.session_id}")
        state.status = SessionStatus.FAILED
        state.error = "Session timed out (Zombie)"
        state.stage = "zombie_cleanup"
        self._persist(state)
    
    def _to_dict(self, state: SessionState) -> Dict:
        """Convert SessionState to dict"""
        return {
            "session_id": state.session_id,
            "status": state.status.value,
            "progress": state.progress,
            "stage": state.stage,
            "title": state.title,
            "mode": state.mode,
            "mode_name": state.mode_name,
            "error": state.error,
            "result_path": state.result_path,
            "created_at": state.created_at.isoformat(),
            "last_updated": state.last_updated.isoformat()
        }


# Singleton lazy initialization
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the SessionManager singleton"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
