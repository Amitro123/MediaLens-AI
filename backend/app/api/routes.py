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
    stt_provider: Optional[str] = "unknown"
    transcript: Optional[str] = None
    transcript_segments: Optional[list] = None 
    frames_count: Optional[int] = None 


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
    return None


from fastapi import BackgroundTasks

async def process_video_background(
    task_id: str,
    video_path: Path,
    options: DevLensAgentOptions
):
    """
    Background task to process video and update progress.
    """
    session_mgr = get_session_manager()
    agent = get_devlens_agent()
    
    try:
        logger.info(f"[BG] Starting processing for {task_id}")
        session_mgr.update_progress(task_id, "initializing", 10)
        
        # Define callback to update session manager
        async def progress_callback(progress: int, stage_label: str):
            session_mgr.update_progress(task_id, stage_label, progress)
            
        result = await agent.generate_documentation(
            session_id=task_id,
            video_path=video_path,
            options=options,
            progress_callback=progress_callback
        )
        
        # Mark as completed
        session_mgr.complete(
            task_id, 
            result_path=None, 
            documentation=result.documentation,
            stt_provider=result.stt_provider,
            transcript=getattr(result, "transcript", None),
            transcript_segments=getattr(result, "transcript_segments", None),
            frames_count=getattr(result, "frames_count", None)
        )
        logger.info(f"[BG] Processing completed for {task_id}")
        
    except Exception as e:
        logger.error(f"[BG] Processing failed for {task_id}: {str(e)}")
        session_mgr.fail(task_id, str(e))


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form("Untitled Project"),
    language: str = Form("en"),
    mode: str = Form("scene_detection"),
    stt_provider: str = Form("auto")
):
    """
    Upload a video file and start background processing.
    Returns immediately with session ID for progress polling.
    """
    task_id = str(uuid.uuid4())
    
    # Initialize session via SessionManager
    session_mgr = get_session_manager()
    session_mgr.create_session(task_id, {
        "project_name": project_name,
        "mode": mode,
        "language": language
    })
    
    logger.info(f"[Upload] Session: {task_id}")
    logger.info(f"[Upload] Mode: {mode}")
    logger.info(f"[Upload] STT Provider: {stt_provider}")
    
    try:
        # Validate file type
        allowed_extensions = {".mp4", ".mov", ".avi", ".webm"}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            session_mgr.fail(task_id, "Invalid file type")
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
        
        # Stream file to disk (better for large files)
        try:
             with open(video_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # 1MB chunks
                    buffer.write(content)
        except Exception as e:
            logger.error(f"File write error: {e}")
            raise HTTPException(status_code=500, detail="Failed to write file to disk")
        
        logger.info(f"Saved video for task {task_id}: {video_path}")
        
        # Update state before starting background task
        session_mgr.update_progress(task_id, "uploaded", 5)
        session_mgr.start_processing(task_id) # Sets to PROCESSING, 0%
        
        # Setup options
        options = DevLensAgentOptions(
            mode=mode,
            language=language,
            project_name=project_name,
            stt_provider=stt_provider
        )
        
        # Start background processing
        background_tasks.add_task(
            process_video_background,
            task_id,
            video_path,
            options
        )
        
        return UploadResponse(
            task_id=task_id,
            status="processing",
            result=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing video: {str(e)}")
        # If session was created, mark it failed using correct method if available
        # But here we might not have a session_mgr instance if it failed early (though we do above)
        try:
            get_session_manager().fail(task_id, str(e))
        except:
            pass
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
        
    raise HTTPException(status_code=404, detail="Task not found")


@router.get("/result/{task_id}", response_model=ResultResponse)
async def get_result(task_id: str):
    """
    Get the generated documentation for a completed task.
    """
    logger.info(f"[DEBUG] Fetching result for task: {task_id}")
    
    # 1. Try task_results first (Manual uploads)
    result = None
    if task_id in task_results:
        result = task_results[task_id]
        logger.info(f"[DEBUG] Found in memory task_results")
    else:
        # 2. Try loading from disk (Universal Persistence Layer)
        storage = get_storage_service()
        result = storage.get_session_result(task_id)
        if result:
             # Cache in memory
            task_results[task_id] = result
            logger.info(f"[DEBUG] Found in persistent storage")

    if result:
         # ADD THESE LOGS:
        logger.info(f"[DEBUG] Result found for {task_id}")
        logger.info(f"[DEBUG] Status: {result.get('status')}")
        
        # Retroactive fix: Calculate frames_count if missing
        if "frames_count" not in result:
             try:
                 upload_path = settings.get_upload_path()
                 frames_dir = upload_path / task_id / "frames"
                 if frames_dir.exists():
                     count = len([f for f in frames_dir.iterdir() if f.suffix in ['.jpg', '.jpeg', '.png']])
                     result["frames_count"] = count
                     logger.info(f"[DEBUG] Calculated frames_count from disk: {count}")
             except Exception as e:
                 logger.warning(f"[DEBUG] Failed to count frames: {e}")
        
        doc = result.get("documentation")
        if doc is not None:
             logger.info(f"[DEBUG] Documentation length: {len(doc)}")
             logger.info(f"[DEBUG] Documentation type: {type(doc)}")
             logger.info(f"[DEBUG] First 200 chars: {str(doc)[:200]}")
        else:
             logger.info(f"[DEBUG] Documentation is None")

        response = ResultResponse(
            task_id=task_id,
            documentation=result["documentation"],
            stt_provider=result.get("stt_provider", "unknown"),
            transcript=result.get("transcript"),
            transcript_segments=result.get("transcript_segments"),
            frames_count=result.get("frames_count")
        )
        return response
        
    logger.warning(f"[DEBUG] No result found for {task_id}")
    raise HTTPException(status_code=404, detail="Task or result not found")


@router.get("/modes")
async def list_modes():
    """
    List all available documentation modes.
    """
    from app.services.prompt_loader import get_prompt_loader
    
    try:
        prompt_loader = get_prompt_loader()
        modes = prompt_loader.get_modes_metadata()
        return {"modes": modes}
    except Exception as e:
        logger.error(f"Failed to list modes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list modes: {str(e)}")


# Endpoint removed: @router.get("/sessions/drafts") - Scheduler deprecated


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
    Legacy endpoint stub.
    """
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
    Deprecated calendar dependencies removed. This now starts a standard session.
    """
    logger.info(f"Received Drive upload request for session {request.session_id}")
    
    # Simple direct processing logic replacment
    raise HTTPException(status_code=501, detail="Drive upload temporarily disabled in MediaLens configuration")


@router.post("/upload/{session_id}")
async def upload_to_session(
    session_id: str,
    file: UploadFile = File(...),
    mode: Optional[str] = Form(None)
):
    """
    Upload a video to a specific session (Legacy draft support removed).
    Redirects to standard upload flow logic if needed.
    """
    # For now, we'll treat this as a new upload using the session_id
    # But standard upload generates its own ID.
    # To support this, we'd need to manually create session logic here.
    # Given requirements, mostly removing complexity.
    
    # Reuse standard upload logic manually
    task_id = session_id
    project_name = f"Session {session_id}"
    selected_mode = mode or "general_doc"
    
    # Initialize session via SessionManager
    session_mgr = get_session_manager()
    session_mgr.create_session(task_id, {
        "project_name": project_name,
        "mode": selected_mode
    })
    session_mgr.start_processing(task_id)
    
    try:
        # Create upload directory
        upload_path = settings.get_upload_path()
        task_dir = upload_path / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        file_ext = Path(file.filename).suffix.lower()
        video_path = task_dir / f"video{file_ext}"
        with open(video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Run agent
        agent = get_devlens_agent()
        options = DevLensAgentOptions(
            mode=selected_mode,
            project_name=project_name
        )
        
        result = await agent.generate_documentation(
            session_id=task_id,
            video_path=video_path,
            options=options
        )
        
        return UploadResponse(
            task_id=result.session_id,
            status=result.status,
            result=result.documentation
        )
        
    except Exception as e:
        logger.error(f"Error in upload_to_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        
    # Check persistent storage
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
    mode: str = "scene_detection"

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


@router.get("/sessions/{session_id}/video")
async def get_session_video(session_id: str, request: Request, range: Optional[str] = Header(None)):
    """Serve the original video file (alias for stream endpoint)."""
    return await stream_video_endpoint(session_id, request, range)


@router.get("/sessions/{session_id}/frames/{frame_id}")
async def get_session_frame(session_id: str, frame_id: str):
    """Serve a specific frame."""
    upload_path = settings.get_upload_path()
    frames_dir = upload_path / session_id / "frames"
    
    if not frames_dir.exists():
        raise HTTPException(status_code=404, detail="Frames directory not found")

    # Clean the ID (remove extension)
    clean_id = frame_id.replace(".jpg", "").replace(".jpeg", "")
    
    frame_path = None
    
    # 1. Try exact match first
    candidate = frames_dir / frame_id
    if candidate.exists():
        frame_path = candidate
    
    # 2. Try constructing standard names
    if not frame_path:
        # If it looks like an index (e.g. "0" or "1")
        if clean_id.isdigit():
            idx = int(clean_id)
            # Look for any file starting with frame_{idx:04d}
            prefix = f"frame_{idx:04d}"
            # Check for files
            for f in frames_dir.iterdir():
                if f.name.startswith(prefix) and f.suffix in [".jpg", ".jpeg", ".png"]:
                    frame_path = f
                    break
    
    # 3. Last ditch: try as direct filename if clean_id wasn't digit
    if not frame_path:
         candidate = frames_dir / f"{clean_id}.jpg"
         if candidate.exists():
             frame_path = candidate

    if not frame_path or not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame not found")
    
    return FileResponse(frame_path, media_type="image/jpeg")


@router.get("/debug/{session_id}")
async def debug_session(session_id: str):
    """Debug endpoint to inspect session data."""
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id)
    
    # Also check persistent storage
    storage = get_storage_service()
    persistent_result = storage.get_session_result(session_id)
    
    return {
        "session_exists": session is not None,
        "status": session.get("status") if session else None,
        "has_result_in_memory": session.get("result") is not None if session else None,
        "has_result_in_storage": persistent_result is not None,
        "documentation_type": type(persistent_result.get("documentation")).__name__ if persistent_result else None,
        "documentation_length": len(persistent_result.get("documentation", "") or "") if persistent_result else 0,
        "first_100_chars": str(persistent_result.get("documentation"))[:100] if persistent_result and persistent_result.get("documentation") else None
    }
