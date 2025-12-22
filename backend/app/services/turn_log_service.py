"""
Turn Log Service for structured session turn logging.

Provides a higher-level view of session content:
- VIDEO_SEGMENT: Transcribed audio segments from Fast STT
- AGENT_NOTE: AI reasoning about relevance/analysis
- DOC_SECTION: Generated documentation sections
"""

import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TurnType(str, Enum):
    """Type of turn in the session log"""
    VIDEO_SEGMENT = "VIDEO_SEGMENT"
    AGENT_NOTE = "AGENT_NOTE"
    DOC_SECTION = "DOC_SECTION"


class SessionTurn(BaseModel):
    """A single turn in the session log"""
    session_id: str
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: TurnType
    segment_id: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    text: Optional[str] = None         # Transcript or note
    markdown: Optional[str] = None     # Final doc section
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True
    
    def to_json_line(self) -> str:
        """Serialize to JSON line for JSONL format"""
        data = self.model_dump()
        # Convert datetime to ISO string
        data["timestamp_utc"] = self.timestamp_utc.isoformat()
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_json_line(cls, line: str) -> "SessionTurn":
        """Deserialize from JSON line"""
        data = json.loads(line)
        # Parse datetime
        if isinstance(data.get("timestamp_utc"), str):
            data["timestamp_utc"] = datetime.fromisoformat(data["timestamp_utc"])
        return cls(**data)


class TurnLogService:
    """
    Service for managing structured turn logs.
    
    Each session has its own JSONL file:
    <base_dir>/<session_id>.jsonl
    """
    
    def __init__(self, base_dir: str = "data/turn_logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TurnLogService initialized: {self.base_dir}")
    
    def _get_log_file(self, session_id: str) -> Path:
        """Get path to session's turn log file"""
        return self.base_dir / f"{session_id}.jsonl"
    
    def append_turn(self, turn: SessionTurn) -> None:
        """
        Append a turn to the session's log file.
        
        Args:
            turn: SessionTurn to append
        """
        log_file = self._get_log_file(turn.session_id)
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(turn.to_json_line() + "\n")
            logger.debug(f"Appended {turn.type} turn to {log_file.name}")
        except Exception as e:
            logger.error(f"Failed to append turn: {e}")
    
    def list_turns(self, session_id: str) -> List[SessionTurn]:
        """
        Read all turns for a session.
        
        Args:
            session_id: Session to read turns for
            
        Returns:
            List of SessionTurn objects
        """
        log_file = self._get_log_file(session_id)
        
        if not log_file.exists():
            return []
        
        turns = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        turns.append(SessionTurn.from_json_line(line))
        except Exception as e:
            logger.error(f"Failed to read turns: {e}")
        
        return turns
    
    def get_log_path(self, session_id: str) -> str:
        """
        Get filesystem path to the turn log.
        
        Args:
            session_id: Session ID
            
        Returns:
            Absolute path to the JSONL file
        """
        return str(self._get_log_file(session_id).resolve())
    
    def get_api_path(self, session_id: str) -> str:
        """
        Get API path to download the turn log.
        
        Args:
            session_id: Session ID
            
        Returns:
            API endpoint path
        """
        return f"/api/v1/sessions/{session_id}/turns"


# Singleton
_turn_log_service: Optional[TurnLogService] = None


def get_turn_log_service() -> TurnLogService:
    """Get or create the TurnLogService singleton"""
    global _turn_log_service
    if _turn_log_service is None:
        _turn_log_service = TurnLogService()
    return _turn_log_service
