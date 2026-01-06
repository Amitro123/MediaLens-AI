"""Unit tests for Storage Service"""
import pytest
from pathlib import Path
import uuid


class TestStorageServiceImport:
    """Test storage service imports"""

    def test_storage_service_import(self):
        """Test storage service can be imported"""
        from app.services.storage_service import StorageService
        assert StorageService is not None

    def test_get_storage_service_singleton(self):
        """Test get_storage_service returns singleton"""
        from app.services.storage_service import get_storage_service
        
        service1 = get_storage_service()
        service2 = get_storage_service()
        
        assert service1 is service2


class TestStorageServicePaths:
    """Test storage service path handling"""

    def test_data_dir_exists(self):
        """Test that data directory is set"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        assert service.data_dir is not None
        assert isinstance(service.data_dir, Path)

    def test_history_file_attribute(self):
        """Test history file attribute exists"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        # Check history file attribute exists
        assert service.history_file is not None
        assert isinstance(service.history_file, Path)

    def test_load_history_returns_dict(self):
        """Test that _load_history returns correct structure"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        history = service._load_history()
        assert history is not None
        assert isinstance(history, dict)
        assert "sessions" in history


class TestStorageOperations:
    """Test storage read/write operations"""

    def test_add_and_get_session(self):
        """Test adding and getting session from history"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        test_id = f"test_storage_{uuid.uuid4().hex[:8]}"
        
        metadata = {
            "title": "Test Session",
            "status": "completed",
            "mode": "general_doc"
        }
        
        # Add session
        service.add_session(test_id, metadata)
        
        # Get history should return a list
        history = service.get_history()
        
        assert history is not None
        assert isinstance(history, list)
        # Check if session is in history
        session_ids = [s.get("id") for s in history]
        assert test_id in session_ids

    def test_list_sessions(self):
        """Test listing sessions"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        sessions = service.list_sessions()
        
        assert sessions is not None
        assert isinstance(sessions, list)

    def test_get_session_result_nonexistent(self):
        """Test getting result for nonexistent session"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        result = service.get_session_result("nonexistent_session_xyz123")
        
        assert result is None

    def test_list_session_frames_nonexistent(self):
        """Test listing frames for nonexistent session"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        frames = service.list_session_frames("nonexistent_session_xyz123")
        
        # Should return empty list for nonexistent session
        assert frames == []

    def test_get_session_details_nonexistent(self):
        """Test getting details for nonexistent session"""
        from app.services.storage_service import get_storage_service
        
        service = get_storage_service()
        
        details = service.get_session_details("nonexistent_session_xyz123")
        
        assert details is None
