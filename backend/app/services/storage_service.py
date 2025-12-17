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

# Singleton lazy initialization
_storage_service = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
