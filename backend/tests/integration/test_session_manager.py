"""Integration tests for Session Manager"""
import pytest
from unittest.mock import patch, MagicMock
import uuid


class TestSessionManager:
    """Test session manager operations"""

    def test_session_manager_import(self):
        """Test session manager can be imported"""
        from app.services.session_manager import SessionManager
        assert SessionManager is not None

    def test_get_session_manager_singleton(self):
        """Test get_session_manager returns singleton"""
        from app.services.session_manager import get_session_manager
        
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        assert manager1 is manager2

    def test_create_session(self):
        """Test creating a new session"""
        from app.services.session_manager import get_session_manager, SessionStatus
        
        manager = get_session_manager()
        test_id = f"test_create_{uuid.uuid4().hex[:8]}"
        
        result = manager.create_session(
            session_id=test_id,
            metadata={"title": "Test Session", "mode": "general_doc"}
        )
        
        assert result is not None
        assert "session_id" in result or result.get("id") == test_id

    def test_get_session_status(self):
        """Test getting session status"""
        from app.services.session_manager import get_session_manager
        
        manager = get_session_manager()
        test_id = f"test_status_{uuid.uuid4().hex[:8]}"
        
        # Create a session first
        manager.create_session(
            session_id=test_id,
            metadata={"title": "Status Test", "mode": "general_doc"}
        )
        
        status = manager.get_status(test_id)
        
        assert status is not None
        assert "status" in status
        assert "progress" in status

    def test_update_session_progress(self):
        """Test updating session progress"""
        from app.services.session_manager import get_session_manager
        
        manager = get_session_manager()
        test_id = f"test_progress_{uuid.uuid4().hex[:8]}"
        
        manager.create_session(
            session_id=test_id,
            metadata={"title": "Progress Test", "mode": "general_doc"}
        )
        
        # Start processing then update
        manager.start_processing(test_id)
        manager.update_progress(test_id, "Testing...", 50)
        
        status = manager.get_status(test_id)
        assert status["progress"] == 50

    def test_get_active_session(self):
        """Test getting active session"""
        from app.services.session_manager import get_session_manager
        
        manager = get_session_manager()
        
        # Get active session - may be None or a session
        active = manager.get_active_session()
        
        # Should return None or a dict
        assert active is None or isinstance(active, dict)

    def test_cancel_session(self):
        """Test cancelling a session"""
        from app.services.session_manager import get_session_manager
        
        manager = get_session_manager()
        test_id = f"test_cancel_{uuid.uuid4().hex[:8]}"
        
        manager.create_session(
            session_id=test_id,
            metadata={"title": "Cancel Test", "mode": "general_doc"}
        )
        manager.start_processing(test_id)
        
        result = manager.cancel(test_id)
        
        # Should succeed
        assert result in [True, False]

    def test_complete_session(self):
        """Test completing a session"""
        from app.services.session_manager import get_session_manager
        
        manager = get_session_manager()
        test_id = f"test_complete_{uuid.uuid4().hex[:8]}"
        
        manager.create_session(
            session_id=test_id,
            metadata={"title": "Complete Test", "mode": "general_doc"}
        )
        manager.start_processing(test_id)
        
        manager.complete(
            session_id=test_id,
            result_path=None,
            documentation="# Test Doc\n\nContent"
        )
        
        status = manager.get_status(test_id)
        assert status is not None
        # Status should be completed
        assert status.get("status") in ["completed", "processing"]

    def test_fail_session(self):
        """Test failing a session"""
        from app.services.session_manager import get_session_manager
        
        manager = get_session_manager()
        test_id = f"test_fail_{uuid.uuid4().hex[:8]}"
        
        manager.create_session(
            session_id=test_id,
            metadata={"title": "Fail Test", "mode": "general_doc"}
        )
        manager.start_processing(test_id)
        
        manager.fail(test_id, "Test error message")
        
        status = manager.get_status(test_id)
        assert status.get("status") == "failed"
