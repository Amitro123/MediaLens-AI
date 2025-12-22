import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """Service for persistent storage of session indices and documentation"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "history.json"
        
        # Initialize history file if it doesn't exist
        if not self.history_file.exists():
            self._save_history({"sessions": []})

    def _load_history(self) -> Dict:
        """Load history from JSON file"""
        try:
            if not self.history_file.exists():
                return {"sessions": []}
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return {"sessions": []}

    def _save_history(self, history: Dict) -> None:
        """Save history to JSON file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def add_session(self, session_id: str, metadata: Dict) -> None:
        """
        Add a session to the persistent history.
        
        Args:
            session_id: Unique session identifier
            metadata: dict containing title, topic, status, mode, etc.
        """
        history = self._load_history()
        
        # Check if session already exists (update if so)
        existing = next((s for s in history["sessions"] if s["id"] == session_id), None)
        
        entry = {
            "id": session_id,
            "timestamp": datetime.now().isoformat(),
            "title": metadata.get("title", f"Session {session_id[:8]}"),
            "topic": metadata.get("topic", "General"),
            "status": metadata.get("status", "completed"),
            "mode": metadata.get("mode", "general_doc"),
            "mode_name": metadata.get("mode_name", "General Documentation")
        }
        
        if existing:
            history["sessions"].remove(existing)
        
        # Add to top of list (recent first)
        history["sessions"].insert(0, entry)
        
        # Save history index
        self._save_history(history)
        
        # Also save the documentation content to the session directory for persistence
        if "documentation" in metadata:
            try:
                upload_path = settings.get_upload_path()
                task_dir = upload_path / session_id
                task_dir.mkdir(parents=True, exist_ok=True)
                
                doc_file = task_dir / "documentation.md"
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(metadata["documentation"])
                logger.debug(f"Saved documentation to {doc_file}")
            except Exception as e:
                logger.error(f"Failed to save documentation artifact: {e}")
                
        logger.info(f"Session {session_id} added to persistent history")

    def get_history(self) -> List[Dict]:
        """Get the full session history"""
        history = self._load_history()
        return history.get("sessions", [])

    def get_session_result(self, session_id: str) -> Optional[Dict]:
        """
        Try to load session result from disk if it was previously saved.
        Returns the data structure expected by task_results.
        """
        # 1. Check history metadata for existence
        history = self._load_history()
        session_meta = next((s for s in history["sessions"] if s["id"] == session_id), None)
        
        if not session_meta:
            return None
            
        # 2. Try to find the documentation artifact on disk
        try:
            upload_path = settings.get_upload_path()
            doc_file = upload_path / session_id / "documentation.md"
            
            if doc_file.exists():
                with open(doc_file, 'r', encoding='utf-8') as f:
                    documentation = f.read()
                
                return {
                    "status": session_meta["status"],
                    "documentation": documentation,
                    "project_name": session_meta["title"],
                    "mode": session_meta["mode"],
                    "mode_name": session_meta["mode_name"]
                }
        except Exception as e:
            logger.error(f"Error loading session result {session_id} from disk: {e}")
            
        return None

    def list_session_frames(self, session_id: str) -> List[Dict]:
        """
        List all extracted frames for a session with their timestamps.
        Returns a list of dicts: { timestamp_sec, thumbnail_url, label }
        """
        try:
            upload_path = settings.get_upload_path()
            frames_dir = upload_path / session_id / "frames"
            
            if not frames_dir.exists():
                return []
                
            frames = []
            for img_path in frames_dir.glob("*.jpg"):
                # Parse timestamp from filename
                # Format 1: frame_0000_t1.0s.jpg (explicit timestamp)
                # Format 2: frame_0012.jpg (legacy, assume 5s interval)
                name = img_path.name
                timestamp = 0.0
                
                if "_t" in name and "s.jpg" in name:
                    # Extract between 't' and 's.jpg'
                    try:
                        t_part = name.split("_t")[1].split("s.jpg")[0]
                        timestamp = float(t_part)
                    except:
                        continue
                elif name.startswith("frame_") and name.endswith(".jpg"):
                    try:
                        # Legacy: frame index * 5
                        idx_part = name.split("frame_")[1].split(".jpg")[0]
                        timestamp = int(idx_part) * 5.0
                    except:
                        continue
                
                frames.append({
                    "timestamp_sec": timestamp,
                    "thumbnail_url": f"/uploads/{session_id}/frames/{name}",
                    "label": f"{int(timestamp//60)}:{int(timestamp%60):02d}"
                })
                
            # Sort by timestamp
            frames.sort(key=lambda x: x["timestamp_sec"])
            return frames
            
        except Exception as e:
            logger.error(f"Error listing frames for {session_id}: {e}")
            return []

    def list_sessions(self) -> List[Dict]:
        """
        Return a lightweight list of sessions for the History tab.
        Each item contains: id, title, status, created_at.
        """
        history = self._load_history()
        sessions = []
        for s in history.get("sessions", []):
            sessions.append({
                "id": s["id"],
                "title": s.get("title") or s.get("id"),
                "status": s.get("status", "UNKNOWN"),
                "created_at": s.get("timestamp"),
            })
        return sessions

    def get_session_details(self, session_id: str) -> Optional[Dict]:
        """
        Build a comprehensive dictionary of session details for the UI.
        Includes metadata, documentation, video_url, and a subset of key frames.
        """
        try:
            # 1. Get metadata
            history = self._load_history()
            session_meta = next((s for s in history["sessions"] if s["id"] == session_id), None)
            
            if not session_meta:
                return None
            
            # 2. Get documentation
            doc_markdown = ""
            upload_path = settings.get_upload_path()
            # Try both "documentation.md" (our current) and "doc.md" (user's suggested)
            doc_file = upload_path / session_id / "documentation.md"
            if not doc_file.exists():
                doc_file = upload_path / session_id / "doc.md"
                
            if doc_file.exists():
                with open(doc_file, 'r', encoding='utf-8') as f:
                    doc_markdown = f.read()
            
            # 3. Get frames (limit to 12 key moments)
            all_frames = self.list_session_frames(session_id)
            num_frames = len(all_frames)
            
            if num_frames > 12:
                # Select 12 evenly spaced frames
                indices = [int(i * (num_frames - 1) / 11) for i in range(12)]
                key_frames = [all_frames[i] for i in indices]
            else:
                key_frames = all_frames
                
            # 4. Load segments (transcription timeline) if available
            segments = []
            segments_file = upload_path / session_id / "segments.json"
            if segments_file.exists():
                try:
                    with open(segments_file, 'r', encoding='utf-8') as f:
                        raw_segments = json.load(f)
                        # Normalize to expected format
                        for seg in raw_segments:
                            segments.append({
                                "start_sec": seg.get("start", seg.get("start_sec", 0)),
                                "end_sec": seg.get("end", seg.get("end_sec", 0)),
                                "text": seg.get("text", "")
                            })
                except Exception as e:
                    logger.warning(f"Failed to load segments for {session_id}: {e}")
                
            # 5. Derive final status from actual state
            # If we have documentation, the session completed successfully regardless of stored status
            stored_status = session_meta.get("status", "UNKNOWN")
            if doc_markdown and len(doc_markdown) > 0:
                final_status = "completed"
            elif stored_status == "failed":
                final_status = "failed"
            elif stored_status in ["processing", "transcribing", "uploading", "downloading"]:
                final_status = "processing"
            else:
                final_status = stored_status
                
            return {
                "id": session_id,
                "title": session_meta.get("title") or session_id,
                "status": final_status,
                "created_at": session_meta.get("timestamp"),
                "mode": session_meta.get("mode"),
                "mode_name": session_meta.get("mode_name"),
                "doc_markdown": doc_markdown,
                "result": doc_markdown,  # Alias for frontend compatibility
                "video_url": f"/api/v1/stream/{session_id}",
                "key_frames": key_frames,
                "segments": segments,
                "pipeline_stages": {
                    "stt": "completed" if final_status == "completed" else "pending",
                    "analysis": "completed" if final_status == "completed" else "pending",
                    "generation": "completed" if final_status == "completed" else "pending"
                }
            }
        except Exception as e:
            logger.error(f"Error building session details for {session_id}: {e}")
            return None
            
# Singleton lazy initialization
_storage_service = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
