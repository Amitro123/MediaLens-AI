"""API routes for video upload and processing"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from pathlib import Path
import uuid
import logging
from typing import Dict, Optional

from app.core.config import settings
from app.services.video_processor import extract_frames, get_video_duration, VideoProcessingError, extract_audio
from app.services.ai_generator import get_generator, AIGenerationError
from app.services.prompt_loader import get_prompt_loader, PromptLoadError
from app.services.storage_service import get_storage_service
from app.services.video_pipeline import process_video_pipeline, PipelineError
from app.core.observability import get_acontext_client, extract_code_blocks, trace_session
from app.core.streaming import video_stream_response
from app.services.native_drive_client import NativeDriveClient
from app.services.session_manager import get_session_manager, SessionStatus
from app.services.agent_orchestrator import get_devlens_agent, DevLensAgentOptions, DevLensResult
from fastapi import Request, Header

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["video"])
minimal_router = APIRouter(prefix="/api", tags=["minimal"])

# In-memory storage for MVP
# TODO: [CR_FINDINGS 2.2] Replace with PostgreSQL/Redis for production persistence
task_results: Dict[str, dict] = {}
session_feedback: Dict[str, list] = {}  # Store feedback by session_id
STALE_TIMEOUT_SECONDS = 600  # 10 minutes timeout for zombie sessions
session_feedback: Dict[str, list] = {}  # Store feedback by session_id


# Note: _store_artifacts moved to video_pipeline.py (CR_FINDINGS 3.1 refactor)


class UploadResponse(BaseModel):
    """Response model for video upload"""
    task_id: str
    status: str
    result: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for task status"""
    status: str
    progress: int
    stage: str = ""  # Current processing stage label


class ResultResponse(BaseModel):
    """Response model for task result"""
    task_id: str
    documentation: str


class FeedbackRequest(BaseModel):
    """Request model for session feedback"""
    rating: int  # 1-5
    comment: Optional[str] = None
    section_id: Optional[str] = None


class ActiveSessionResponse(BaseModel):
    """Response model for active session recovery"""
    session_id: str
    status: str
    title: str
    mode: Optional[str] = None
    progress: int = 0



@router.get("/active-session", response_model=Optional[ActiveSessionResponse])
async def get_active_session():
    """
    Check for any active processing or uploading session.
    Delegates to centralized SessionManager.
    """
    session_mgr = get_session_manager()
    active = session_mgr.get_active_session()
    
    if active:
        return ActiveSessionResponse(
            session_id=active["session_id"],
            status=active["status"],
            title=active["title"],
            mode=active.get("mode"),
            progress=active.get("progress", 0)
        )
    
    # Fallback: Check calendar sessions for backwards compatibility
    try:
        from app.services.calendar_service import get_calendar_watcher
        calendar = get_calendar_watcher()
        drafts = calendar.get_draft_sessions()
        
        active_statuses = ["processing", "downloading_from_drive", "uploading"]
        for s in drafts:
            if s.status in active_statuses:
                logger.info(f"Active session found in calendar: {s.session_id}")
                status_info = session_mgr.get_status(s.session_id)
                progress = status_info.get("progress", 0) if status_info else 0
                
                return ActiveSessionResponse(
                    session_id=s.session_id,
                    status=s.status,
                    title=s.title,
                    mode=s.suggested_mode,
                    progress=progress
                )
    except Exception as e:
        logger.error(f"Error checking calendar sessions: {e}")
    
    return None


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    project_name: str = Form("Untitled Project"),
    language: str = Form("en"),
    mode: str = Form("general_doc")
):
    """
    Upload a video file and generate documentation.
    
    For MVP: Processes synchronously and returns result immediately.
    Future: Will queue task to Celery and return task_id for async processing.
    
    Args:
        file: Video file (mp4, mov, avi, webm)
        project_name: Name of the project being documented
        language: Language for documentation (en/he)
        mode: Documentation mode (bug_report, feature_spec, general_doc)
    
    Returns:
        UploadResponse with task_id and generated documentation
    """
    task_id = str(uuid.uuid4())
    
    # Initialize session via SessionManager
    session_mgr = get_session_manager()
    session_mgr.create_session(task_id, {
        "project_name": project_name,
        "mode": mode
    })
    session_mgr.start_processing(task_id)
    
    try:
        # Validate file type
        allowed_extensions = {".mp4", ".mov", ".avi", ".webm"}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Create upload directory
        upload_path = settings.get_upload_path()
        task_dir = upload_path / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        video_path = task_dir / f"video{file_ext}"
        with open(video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Saved video for task {task_id}: {video_path}")
        
        # Use DevLensAgent for orchestration
        agent = get_devlens_agent()
        options = DevLensAgentOptions(
            mode=mode,
            language=language,
            project_name=project_name
        )
        
        try:
            result = await agent.generate_documentation(
                session_id=task_id,
                video_path=video_path,
                options=options
            )
        except PipelineError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except PromptLoadError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        return UploadResponse(
            task_id=result.session_id,
            status=result.status,
            result=result.documentation
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """
    Get the status of a processing task.
    Delegates to centralized SessionManager.
    """
    session_mgr = get_session_manager()
    status_info = session_mgr.get_status(task_id)
    
    if status_info:
        return StatusResponse(
            status=status_info["status"],
            progress=status_info["progress"],
            stage=status_info.get("stage", "")
        )
    
    # Fallback: Check calendar sessions for backwards compatibility
    try:
        from app.services.calendar_service import get_calendar_watcher
        calendar = get_calendar_watcher()
        session = calendar.get_session(task_id)
        if session:
            progress = 0
            stage = ""
            if session.status == "completed": 
                progress = 100
                stage = "Complete!"
            elif session.status == "processing": 
                progress = 60
                stage = "Processing..."
            elif session.status == "downloading_from_drive": 
                progress = 30
                stage = "Downloading from Drive..."
            
            return StatusResponse(
                status=session.status,
                progress=progress,
                stage=stage
            )
    except:
        pass
        
    raise HTTPException(status_code=404, detail="Task not found")


@router.get("/result/{task_id}", response_model=ResultResponse)
async def get_result(task_id: str):
    """
    Get the generated documentation for a completed task.
    """
    # 1. Try task_results first (Manual uploads)
    if task_id in task_results:
        result = task_results[task_id]
        if result["status"] == "completed":
            return ResultResponse(
                task_id=task_id,
                documentation=result["documentation"]
            )
    
    # 2. Try Draft Sessions (Calendar/Drive flows)
    try:
        from app.services.calendar_service import get_calendar_watcher
        calendar = get_calendar_watcher()
        session = calendar.get_session(task_id)
        if session and session.status == "completed":
            # Data might be in metadata or on disk
            documentation = session.metadata.get("documentation")
            if documentation:
                return ResultResponse(task_id=task_id, documentation=documentation)
    except:
        pass

    # 3. Try loading from disk (Universal Persistence Layer)
    storage = get_storage_service()
    persisted_result = storage.get_session_result(task_id)
    if persisted_result:
        # Cache in memory
        task_results[task_id] = persisted_result
        return ResultResponse(
            task_id=task_id,
            documentation=persisted_result["documentation"]
        )
        
    raise HTTPException(status_code=404, detail="Task or result not found")


@router.get("/modes")
async def list_modes():
    """
    List all available documentation modes.
    
    Returns:
        List of available modes with metadata (mode, name, description)
    """
    from app.services.prompt_loader import get_prompt_loader
    
    try:
        prompt_loader = get_prompt_loader()
        modes = prompt_loader.get_modes_metadata()
        return {"modes": modes}
    except Exception as e:
        logger.error(f"Failed to list modes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list modes: {str(e)}")


@router.get("/sessions/drafts")
async def get_draft_sessions():
    """
    Get all draft sessions created from calendar events.
    Returns a list of mock events as requested by the frontend.
    """
    from app.services.calendar_service import get_calendar_watcher
    
    try:
        calendar = get_calendar_watcher()
        # Get all sessions that are not completed/failed
        drafts = calendar.get_draft_sessions()
        
        # Filter for relevant statuses for the selector
        active_drafts = [
            s for s in drafts 
            if s.status in ["scheduled", "ready_for_upload", "processing", "waiting_for_upload"]
        ]
        
        return [
            {
                "id": s.session_id,
                "title": s.title,
                "time": s.metadata.get("event_start", ""),
                "status": s.status if s.status != "waiting_for_upload" else "scheduled",
                "context_keywords": s.context_keywords
            }
            for s in active_drafts
        ]
    except Exception as e:
        logger.error(f"Failed to fetch draft sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str):
    """
    Get detailed information for a specific session.
    Unified endpoint for both active and checking archived sessions.
    """
    # 1. Check Active Sessions (in-memory)
    session_mgr = get_session_manager()
    active = session_mgr.get_active_session()
    
    if active and active["session_id"] == session_id:
        return {
            "id": active["session_id"],
            "title": active["title"],
            "status": active["status"],
            "created_at": active.get("created_at"),
            "mode": active.get("mode"),
            "doc_markdown": None, # Usually not ready until complete
            "video_url": None,
            "turn_log_path": None,
            "pipeline_stages": {
                "stt": "processing" if active["progress"] < 30 else "completed",
                "analysis": "processing" if 30 <= active["progress"] < 70 else "pending",
                "generation": "processing" if active["progress"] >= 70 else "pending"
            }
        }

    # 2. Check Persisted/Archived Sessions (storage)
    try:
        storage = get_storage_service()
        session_details = await run_in_threadpool(storage.get_session_details, session_id)
        
        if session_details:
            return session_details
            
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}")
        
    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.get("/sessions/{session_id}/turns")
async def get_session_turns(session_id: str):
    """Download the turn log for a session (JSONL)."""
    file_path = Path("data/timelines") / f"{session_id}.jsonl"
    if not file_path.exists():
         raise HTTPException(status_code=404, detail="Turn log not found")
    return FileResponse(file_path, media_type="application/json", filename=f"{session_id}_turns.jsonl")


@router.get("/history")
async def get_history():
    """
    Get the list of all past documentation sessions.
    """
    logger.info("Fetching session history...")
    try:
        storage = get_storage_service()
        # Use run_in_threadpool for file I/O which might be slow/locked on Windows
        sessions = await run_in_threadpool(storage.get_history)
        logger.info(f"Successfully fetched {len(sessions)} history sessions")
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load history: {str(e)}")


@router.post("/sessions/{session_id}/prep")
async def prep_session(session_id: str):
    """
    Prepare a session for upload (update status to ready_for_upload).
    """
    from app.services.calendar_service import get_calendar_watcher
    
    calendar = get_calendar_watcher()
    session = calendar.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update status to ready_for_upload
    # This signifies that the context is "primed"
    calendar.update_session_status(session_id, "ready_for_upload")
    
    return {"status": "ready_for_upload", "id": session_id}

class DriveUploadRequest(BaseModel):
    """Request model for Drive upload"""
    url: str
    session_id: str
    access_token: Optional[str] = None


@router.post("/upload/drive", response_model=UploadResponse)
async def upload_from_drive(request: DriveUploadRequest):
    """
    Import video from Google Drive and generate documentation.
    
    Uses shared video processing pipeline (CR_FINDINGS 3.1 refactor).
    """
    logger.info(f"Received Drive upload request for session {request.session_id}")
    
    try:
        from app.services.calendar_service import get_calendar_watcher
        from app.services.drive_connector import DriveConnector, DriveError
        
        calendar = get_calendar_watcher()
        session = calendar.get_session(request.session_id)
        
        if not session:
            logger.error(f"Session {request.session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
            
        # Initialize Drive connector
        connector = DriveConnector()
        file_id = connector.extract_file_id(request.url)
        
        if not file_id:
            logger.error(f"Invalid Google Drive URL: {request.url}")
            raise HTTPException(status_code=400, detail="Invalid Google Drive URL. Could not extract file ID.")
            
        logger.info(f"Extracted file ID: {file_id}")
        
        # Update session status
        calendar.update_session_status(request.session_id, "downloading_from_drive")
        
        # Prepare paths
        upload_path = settings.get_upload_path()
        task_dir = upload_path / request.session_id
        task_dir.mkdir(parents=True, exist_ok=True)
        video_path = task_dir / "video.mp4"
        
        # Download file
        try:
            connector.download_file(file_id, video_path, request.access_token)
        except DriveError as e:
            calendar.update_session_status(request.session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=400, detail=str(e))
        
        # Load prompt with session context
        selected_mode = session.suggested_mode or "general_doc"
        prompt_loader = get_prompt_loader()
        context = {
            "meeting_title": session.title,
            "attendees": ", ".join(session.attendees),
            "keywords": ", ".join(session.context_keywords)
        }
        prompt_config = prompt_loader.load_prompt(selected_mode, context=context)
        
        calendar.update_session_status(request.session_id, "processing")
        
        # Use shared processing pipeline
        try:
            result = await process_video_pipeline(
                video_path=video_path,
                task_id=request.session_id,
                prompt_config=prompt_config,
                project_name=session.title,
                context_keywords=session.context_keywords,
                mode=selected_mode
            )
        except PipelineError as e:
            calendar.update_session_status(request.session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))
        
        # Update session status
        calendar.update_session_status(
            request.session_id,
            "completed",
            {
                "documentation": result.documentation,
                "mode_used": result.mode,
                "mode_name": result.mode_name
            }
        )
        
        return UploadResponse(
            task_id=result.task_id,
            status=result.status,
            result=result.documentation
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Drive upload: {e}")
        # Ensure status is updated on failure
        try:
            calendar = get_calendar_watcher()
            calendar.update_session_status(request.session_id, "failed", {"error": str(e)})
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/upload/{session_id}")
async def upload_to_session(
    session_id: str,
    file: UploadFile = File(...),
    mode: Optional[str] = Form(None)
):
    """
    Upload a video to a specific draft session.
    
    Args:
        session_id: ID of the draft session
        file: Video file to upload
        mode: Optional mode override (uses session's suggested_mode if not provided)
    
    Returns:
        UploadResponse with generated documentation
    """
    from app.services.calendar_service import get_calendar_watcher
    from app.services.prompt_loader import get_prompt_loader, PromptLoadError
    
    try:
        # Get the session
        calendar = get_calendar_watcher()
        session = calendar.get_session(session_id)
        
        if not session:
            # Lazy creation for development/mock compatibility
            logger.info(f"Session {session_id} not found, lazily creating...")
            from app.services.calendar_service import DraftSession
            from datetime import datetime, timedelta
            
            session = DraftSession(
                session_id=session_id,
                event_id=f"evt_mock_{session_id}",
                title=f"Session {session_id}",
                attendees=["user@example.com"],
                context_keywords=["general"],
                status="ready_for_upload",
                created_at=datetime.now(),
                suggested_mode="general_doc",
                metadata={
                    "event_start": datetime.now().isoformat(),
                    "event_end": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "description": "Auto-created session from upload"
                }
            )
            # Inject into calendar
            calendar.draft_sessions[session_id] = session
        
        # Allow upload for both waiting and ready states
        allowed_statuses = {"waiting_for_upload", "ready_for_upload"}
        if session.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} is not ready for upload (status: {session.status})"
            )
        
        # Determine mode (use provided or session's suggested mode)
        selected_mode = mode or session.suggested_mode or "general_doc"
        
        # Load prompt with session context
        try:
            prompt_loader = get_prompt_loader()
            context = {
                "meeting_title": session.title,
                "attendees": ", ".join(session.attendees),
                "keywords": ", ".join(session.context_keywords)
            }
            prompt_config = prompt_loader.load_prompt(selected_mode, context=context)
            logger.info(f"Loaded prompt mode: {selected_mode} with context for session {session_id}")
        except PromptLoadError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Update session status
        calendar.update_session_status(session_id, "processing")
        
        # Validate file type
        allowed_extensions = {".mp4", ".mov", ".avi", ".webm"}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            calendar.update_session_status(session_id, "failed", {"error": "Invalid file type"})
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Create upload directory
        upload_path = settings.get_upload_path()
        task_dir = upload_path / session_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        video_path = task_dir / f"video{file_ext}"
        with open(video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Saved video for session {session_id}: {video_path}")

        # Initialize session in SessionManager
        session_mgr = get_session_manager()
        session_mgr.create_session(session_id, {
            "title": session.title,
            "mode": selected_mode
        })
        session_mgr.start_processing(session_id)
        
        # Use DevLensAgent for orchestration
        agent = get_devlens_agent()
        options = DevLensAgentOptions(
            mode=selected_mode,
            project_name=session.title,
            calendar_event_id=session_id  # Pass event ID for context enrichment
        )
        
        try:
            result = await agent.generate_documentation(
                session_id=session_id,
                video_path=video_path,
                options=options
            )
        except PipelineError as e:
            calendar.update_session_status(session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=500, detail=str(e))
        
        # Update calendar session for backwards compatibility
        calendar.update_session_status(
            session_id,
            "completed",
            {
                "documentation": result.documentation,
                "mode_used": result.mode,
                "mode_name": result.mode_name
            }
        )
        
        return UploadResponse(
            task_id=result.session_id,
            status=result.status,
            result=result.documentation
        )
    
    except HTTPException:
        raise


@router.post("/sessions/{session_id}/feedback")
async def submit_feedback(session_id: str, feedback: FeedbackRequest):
    """
    Submit user feedback for a generated documentation session.
    """
    if feedback.rating < 1 or feedback.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Initialize list if not exists
    if session_id not in session_feedback:
        session_feedback[session_id] = []
    
    # Allow multiple feedback entries (e.g. for different sections)
    feedback_entry = {
        "rating": feedback.rating,
        "comment": feedback.comment,
        "section_id": feedback.section_id,
        "timestamp": str(uuid.uuid4())  # Mock timestamp
    }
    
    session_feedback[session_id].append(feedback_entry)
    
    logger.info(f"Received feedback for session {session_id}: {feedback.rating}/5")
    
    return {"status": "success", "message": "Feedback received"}


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(session_id: str):
    """
    Cancel an active processing session.
    Delegates to SessionManager.
    """
    logger.info(f"Requesting cancellation for session {session_id}")
    
    session_mgr = get_session_manager()
    cancelled = session_mgr.cancel(session_id)
        
    # 2. Check Calendar/Draft sessions
    from app.services.calendar_service import get_calendar_watcher
    calendar = get_calendar_watcher()
    session = calendar.get_session(session_id)
    if session and session.status in ["processing", "uploading", "waiting_for_upload"]:
        calendar.update_session_status(session_id, "cancelled")
        logger.info(f"Cancelled calendar session {session_id}")
        cancelled = True

    # 3. Update persistent storage if it exists there
    from app.services.storage_service import get_storage_service
    storage = get_storage_service()
    history = storage.get_history()
    # Find active session in history
    persistent_session = next((s for s in history if s["id"] == session_id), None)
    if persistent_session and persistent_session.get("status") in ["processing", "uploading"]:
         storage.add_session(session_id, {
             **persistent_session,
             "status": "cancelled"
         })
         logger.info(f"Cancelled persistent session {session_id}")
         cancelled = True
         
    if cancelled:
        return {"status": "success", "message": "Session cancelled"}
    else:
        # If we didn't find anything to cancel, verify if it was already stale/done
        # But we return 200 to be idempotent for the UI
        return {"status": "success", "message": "Session not found or already completed"}


class ExportRequest(BaseModel):
    """Request model for session export"""
    target: str  # "jira" or "notion" or "clipboard"


@router.post("/sessions/{session_id}/export")
async def export_session(session_id: str, request: ExportRequest):
    """
    Export generated documentation to external services (Mock implementation).
    """
    target = request.target.lower()
    
    if target not in ["jira", "notion", "clipboard"]:
        raise HTTPException(status_code=400, detail="Invalid export target. Use 'jira', 'notion', or 'clipboard'")
    
    # Get session details (for title)
    session_title = f"Session {session_id[:8]}"  # Mock session title
    
    # Mock export logic
    if target == "jira":
        ticket_id = f"BUG-{session_id[:4].upper()}"
        logger.info(f"[MOCK EXPORT] Ticket Created: [{ticket_id}] - {session_title}")
        return {
            "status": "success",
            "message": f"Jira ticket created: {ticket_id}",
            "ticket_id": ticket_id
        }
    
    elif target == "notion":
        page_url = f"https://notion.so/Engineering-Docs/{session_id}"
        logger.info(f"[MOCK EXPORT] Page Created in 'Engineering Docs': {session_title}")
        return {
            "status": "success",
            "message": f"Notion page created: {session_title}",
            "page_url": page_url
        }
    



@router.get("/stream/{task_id}")
async def stream_video_endpoint(task_id: str, request: Request, range: Optional[str] = Header(None)):
    """
    Stream video with Range support (required for seeking).
    """
    try:
        upload_path = settings.get_upload_path()
        # Handle both draft sessions (might store video in task_dir) and manual uploads
        # Manual/Normal structure: uploads/{task_id}/video.mp4
        
        video_path = upload_path / task_id / "video.mp4"
        
        if not video_path.exists():
             # Fallback check for extensions
             for ext in [".mov", ".avi", ".webm"]:
                 p = upload_path / task_id / f"video{ext}"
                 if p.exists():
                     video_path = p
                     break

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
            
        return video_stream_response(str(video_path), range)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrations/drive/files")
async def list_drive_files():
    """
    List video files available in Google Drive via MCP.
    """
    try:
        client = NativeDriveClient()
        files = await client.list_files()
        return {"files": files}
    except Exception as e:
         logger.error(f"MCP List Error: {e}")
         # Return empty list or mock instead of 500 to keep UI stable
         return {"files": [], "error": str(e)}

class DriveImportRequest(BaseModel):
    file_uri: str
    file_name: str
    mode: str = "general_doc"

@router.post("/import/drive")
async def import_drive_file(request: DriveImportRequest):
    """
    Import a file from Drive (MCP) and start processing.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"Starting Drive import for {request.file_name} ({request.file_uri})")
    
    # Initialize session
    from app.services.calendar_service import DraftSession
    from app.services.storage_service import get_storage_service
    from datetime import datetime
    
    # Create persistent session entry
    storage = get_storage_service()
    storage.add_session(task_id, {
        "title": f"Import: {request.file_name}",
        "topic": "Drive Import",
        "status": "downloading", # New status
        "mode": request.mode,
        "progress": 0,
        "last_updated": datetime.now().isoformat()
    })
    
    # In-memory tracking
    task_results[task_id] = {
        "status": "downloading",
        "project_name": request.file_name,
        "mode": request.mode,
        "progress": 0,
        "last_updated": datetime.now()
    }
    
    try:
        # Prepare paths
        upload_path = settings.get_upload_path()
        task_dir = upload_path / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        video_path = task_dir / "video.mp4"
        
        # Download via Native Client
        client = NativeDriveClient()
        await client.download_file(request.file_uri, video_path)
        
        # Update status to processing
        task_results[task_id]["status"] = "processing"
        task_results[task_id]["progress"] = 10
        
        # Determine prompt config
        from app.services.prompt_loader import get_prompt_loader
        prompt_loader = get_prompt_loader()
        prompt_config = prompt_loader.load_prompt(request.mode)
        
        # Run pipeline
        # Note: In production this should be a background task (Celery)
        # For MVP we await it (blocking HTTP response, but we have ThreadPool in pipeline)
        result = await process_video_pipeline(
            video_path=video_path,
            task_id=task_id,
            prompt_config=prompt_config,
            project_name=request.file_name,
            context_keywords=["drive-import"],
            mode=request.mode
        )
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result": result.documentation
        }

    except Exception as e:
        logger.error(f"Drive Import Failed: {e}")
        task_results[task_id]["status"] = "failed"
        task_results[task_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))







@minimal_router.get("/sessions")
async def list_sessions_minimal():
    """List sessions for the History tab (minimal endpoint)."""
    storage = get_storage_service()
    return await run_in_threadpool(storage.list_sessions)


@minimal_router.get("/sessions/{session_id}")
async def get_session_minimal(session_id: str):
    """Get full session details for History details view (minimal endpoint)."""
    storage = get_storage_service()
    details = await run_in_threadpool(storage.get_session_details, session_id)
    if not details:
        raise HTTPException(status_code=404, detail="Session not found")
    return details
