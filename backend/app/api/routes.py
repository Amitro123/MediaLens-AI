"""API routes for video upload and processing"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
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
from app.core.observability import get_acontext_client, extract_code_blocks, trace_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["video"])

# In-memory storage for MVP
# TODO: [CR_FINDINGS 2.2] Replace with PostgreSQL/Redis for production persistence
task_results: Dict[str, dict] = {}
session_feedback: Dict[str, list] = {}  # Store feedback by session_id


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


class UploadResponse(BaseModel):
    """Response model for video upload"""
    task_id: str
    status: str
    result: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for task status"""
    status: str
    progress: int


class ResultResponse(BaseModel):
    """Response model for task result"""
    task_id: str
    documentation: str


class FeedbackRequest(BaseModel):
    """Request model for session feedback"""
    rating: int  # 1-5
    comment: Optional[str] = None
    section_id: Optional[str] = None


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
    
    try:
        # Load prompt configuration
        from app.services.prompt_loader import get_prompt_loader, PromptLoadError
        
        try:
            prompt_loader = get_prompt_loader()
            prompt_config = prompt_loader.load_prompt(mode)
            logger.info(f"Loaded prompt mode: {mode} - {prompt_config.name}")
        except PromptLoadError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
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
        
        # Validate video duration
        try:
            duration = await run_in_threadpool(get_video_duration, str(video_path))
            if duration > settings.max_video_length:
                raise HTTPException(
                    status_code=400,
                    detail=f"Video too long. Maximum: {settings.max_video_length}s ({settings.max_video_length // 60} minutes)"
                )
            logger.info(f"Video duration: {duration:.2f}s")
        except VideoProcessingError as e:
            raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")
        
        # Extract frames
        frames_dir = task_dir / "frames"
        try:
            frame_paths = await run_in_threadpool(
                extract_frames,
                str(video_path),
                str(frames_dir),
                settings.frame_interval
            )
            logger.info(f"Extracted {len(frame_paths)} frames")
        except VideoProcessingError as e:
            raise HTTPException(status_code=500, detail=f"Frame extraction failed: {str(e)}")
        
        # Generate documentation with dynamic prompt
        try:
            generator = get_generator()
            documentation = generator.generate_documentation(
                frame_paths=frame_paths,
                prompt_config=prompt_config,
                context="",  # TODO: Add RAG context retrieval
                project_name=project_name
            )
            logger.info(f"Generated documentation for task {task_id}")
        except AIGenerationError as e:
            raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
        
        # Store result
        task_results[task_id] = {
            "status": "completed",
            "documentation": documentation,
            "project_name": project_name,
            "language": language,
            "mode": mode,
            "mode_name": prompt_config.name
        }
        
        # Store artifacts in Acontext (Flight Recorder)
        _store_artifacts(task_id, documentation, project_name)
        
        # PERSIST TO HISTORY
        storage = get_storage_service()
        storage.add_session(task_id, {
            "title": project_name,
            "topic": prompt_config.name,
            "status": "completed",
            "documentation": documentation,
            "mode": mode,
            "mode_name": prompt_config.name
        })
        
        return UploadResponse(
            task_id=task_id,
            status="completed",
            result=documentation
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
    
    Args:
        task_id: Unique task identifier
    
    Returns:
        StatusResponse with current status and progress
    """
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_results[task_id]
    
    return StatusResponse(
        status=result["status"],
        progress=100 if result["status"] == "completed" else 0
    )


@router.get("/result/{task_id}", response_model=ResultResponse)
async def get_result(task_id: str):
    """
    Get the generated documentation for a completed task.
    
    Args:
        task_id: Unique task identifier
    
    Returns:
        ResultResponse with generated documentation
    """
    if task_id not in task_results:
        # Try loading from disk (Persistence Layer)
        storage = get_storage_service()
        persisted_result = storage.get_session_result(task_id)
        if persisted_result:
            # Cache in memory for next time
            task_results[task_id] = persisted_result
            return ResultResponse(
                task_id=task_id,
                documentation=persisted_result["documentation"]
            )
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_results[task_id]
    
    if result["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")
    
    return ResultResponse(
        task_id=task_id,
        documentation=result["documentation"]
    )


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


@router.get("/history")
async def get_history():
    """
    Get the list of all past documentation sessions.
    """
    try:
        storage = get_storage_service()
        return {"sessions": storage.get_history()}
    except Exception as e:
        logger.error(f"Failed to fetch history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load history")


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
        # We don't know extension yet, assuming mp4 for now or rely on file headers later
        # But DriveConnector just streams bytes. Let's use a temporary name or default to mp4.
        # Ideally we'd get metadata first, but for MVP let's assume video.mp4
        video_path = task_dir / "video.mp4"
        
        # Download file
        try:
            connector.download_file(file_id, video_path, request.access_token)
        except DriveError as e:
            calendar.update_session_status(request.session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=400, detail=str(e))
            
        # Trigger processing pipeline (Reuse logic or call a shared function)
        # Ideally, we should refactor upload_to_session to separate "get file" from "process file".
        # For now, we'll duplicate the processing/call logic or invoke it if we refactor.
        # Given the constraint to just "trigger existing process", let's replicate the critical steps:
        # 1. Load Prompt
        # 2. Get Duration
        # 3. Audio Extraction
        # 4. Smart/Regular Frame Extraction
        # 5. Generation
        
        # --- Shared Processing Logic ---
        # Determine mode
        selected_mode = session.suggested_mode or "general_doc"
        
        # Load prompt
        prompt_loader = get_prompt_loader()
        context = {
            "meeting_title": session.title,
            "attendees": ", ".join(session.attendees),
            "keywords": ", ".join(session.context_keywords)
        }
        prompt_config = prompt_loader.load_prompt(selected_mode, context=context)
        
        calendar.update_session_status(request.session_id, "processing")
        
        # Validate video duration
        duration = await run_in_threadpool(get_video_duration, str(video_path))
        if duration > settings.max_video_length:
             raise HTTPException(status_code=400, detail="Video too long")

        # Audio-First Pipeline
        generator = get_generator()
        relevant_segments = None
        
        try:
            audio_path = await run_in_threadpool(extract_audio, str(video_path))
            relevant_segments = generator.analyze_audio_relevance(
                audio_path, context_keywords=session.context_keywords
            )
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")
            
        # Frame Extraction
        frames_dir = task_dir / "frames"
        timestamps = None
        if relevant_segments:
            timestamps = []
            for seg in relevant_segments:
                timestamps.append(seg['start'])
                timestamps.append(seg['end'])
        
        frame_paths = await run_in_threadpool(
            extract_frames,
            str(video_path), 
            str(frames_dir), 
            settings.frame_interval,
            timestamps
        )
        
        # Generate Docs
        documentation = generator.generate_documentation(
            frame_paths=frame_paths,
            prompt_config=prompt_config,
            project_name=session.title
        )
        
        # Complete
        calendar.update_session_status(
            request.session_id,
            "completed",
            {
                "documentation": documentation,
                "mode_used": selected_mode,
                "mode_name": prompt_config.name
            }
        )
        
        # Store artifacts in Acontext (Flight Recorder)
        _store_artifacts(request.session_id, documentation, session.title)
        
        # PERSIST TO HISTORY
        storage = get_storage_service()
        storage.add_session(request.session_id, {
            "title": session.title,
            "topic": prompt_config.name,
            "status": "completed",
            "documentation": documentation,
            "mode": selected_mode,
            "mode_name": prompt_config.name
        })
        
        return UploadResponse(
            task_id=request.session_id,
            status="completed",
            result=documentation
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
        
        # Validate video duration
        try:
            duration = await run_in_threadpool(get_video_duration, str(video_path))
            if duration > settings.max_video_length:
                calendar.update_session_status(session_id, "failed", {"error": "Video too long"})
                raise HTTPException(
                    status_code=400,
                    detail=f"Video too long. Maximum: {settings.max_video_length}s"
                )
            logger.info(f"Video duration: {duration:.2f}s")
        except VideoProcessingError as e:
            calendar.update_session_status(session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")
        
        # --- Audio-First Pipeline ---
        generator = get_generator()
        relevant_segments = []
        
        # 1. Extract Audio
        try:
            logger.info("Starting Audio-First Analysis...")
            audio_path = await run_in_threadpool(extract_audio, str(video_path))
            
            # 2. Analyze Audio Relevance (Gemini Flash)
            relevant_segments = generator.analyze_audio_relevance(
                audio_path,
                context_keywords=session.context_keywords
            )
        except Exception as e:
            logger.warning(f"Audio analysis failed, falling back to regular sampling: {e}")
            # Fallback will happen naturally if relevant_segments is empty/None
            relevant_segments = None

        # 3. Smart Frame Extraction
        frames_dir = task_dir / "frames"
        try:
            # Convert segments to timestamps list
            timestamps = None
            if relevant_segments:
                timestamps = []
                for seg in relevant_segments:
                    # Extract frames at start, middle, and end
                    timestamps.append(seg['start'])
                    if seg['end'] - seg['start'] > 5.0:
                        timestamps.append((seg['start'] + seg['end']) / 2)
                    timestamps.append(seg['end'])
                
                logger.info(f"Smart Sampling: Extracting at {len(timestamps)} specific timestamps")
            
            frame_paths = await run_in_threadpool(
                extract_frames,
                str(video_path),
                str(frames_dir),
                settings.frame_interval,
                timestamps
            )
            logger.info(f"Extracted {len(frame_paths)} frames")
        except VideoProcessingError as e:
            calendar.update_session_status(session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=500, detail=f"Frame extraction failed: {str(e)}")
        
        # 4. Generate documentation with context-aware prompt
        try:
            documentation = generator.generate_documentation(
                frame_paths=frame_paths,
                prompt_config=prompt_config,
                context="",  # RAG context (future)
                project_name=session.title
            )
            logger.info(f"Generated documentation for session {session_id}")
        except AIGenerationError as e:
            calendar.update_session_status(session_id, "failed", {"error": str(e)})
            raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
        
        # Update session status
        calendar.update_session_status(
            session_id,
            "completed",
            {
                "documentation": documentation,
                "mode_used": selected_mode,
                "mode_name": prompt_config.name
            }
        )
        
        # Store artifacts in Acontext (Flight Recorder)
        _store_artifacts(session_id, documentation, session.title)
        
        # PERSIST TO HISTORY
        storage = get_storage_service()
        storage.add_session(session_id, {
            "title": session.title,
            "topic": prompt_config.name,
            "status": "completed",
            "documentation": documentation,
            "mode": selected_mode,
            "mode_name": prompt_config.name
        })
        
        return UploadResponse(
            task_id=session_id,
            status="completed",
            result=documentation
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
    
    else:  # clipboard
        return {
            "status": "success",
            "message": "Content copied to clipboard"
        }







