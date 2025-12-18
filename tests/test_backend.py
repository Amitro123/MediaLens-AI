import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import io

@pytest.fixture
def dummy_video():
    """Create a dummy video file content"""
    return io.BytesIO(b"dummy mp4 content")

@patch("app.api.routes.process_video_pipeline")
@patch("app.api.routes.get_video_duration")
def test_upload_video(mock_duration, mock_pipeline, client, dummy_video):
    """
    Test 1: Upload a dummy .mp4 file to /api/v1/upload/{id} 
    and assert 200 OK and file existence.
    """
    # Setup mocks
    mock_duration.return_value = 10.0
    mock_pipeline.return_value = MagicMock(
        task_id="test_session_123",
        status="completed",
        documentation="# Test Doc",
        mode="general_doc",
        mode_name="General Documentation"
    )
    
    session_id = "test_session_123"
    files = {"file": ("test.mp4", dummy_video, "video/mp4")}
    
    response = client.post(f"/api/v1/upload/{session_id}", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == session_id
    assert data["status"] == "completed"
    assert "result" in data
    
    # Check that video file was "saved" (in mock context, the directory should exist)
    # The routes.py creates the directory using settings.get_upload_path() / session_id
    from app.core.config import settings
    upload_path = Path(settings.upload_dir) / session_id
    assert upload_path.exists()
    assert (upload_path / "video.mp4").exists()

def test_status_endpoint(client):
    """
    Test 2: Check that /api/v1/status/{id} returns valid JSON.
    """
    # We need to prime the task_results or CalendarWatcher
    # Since task_results is in-memory in routes.py, we can just call an upload first 
    # or mock the status retrieval.
    
    # For simplicity, let's mock a session in the calendar
    with patch("app.services.calendar_service.CalendarWatcher.get_session") as mock_get_session:
        mock_session = MagicMock()
        mock_session.status = "processing"
        mock_get_session.return_value = mock_session
        
        response = client.get("/api/v1/status/test_task_456")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data
        assert data["status"] == "processing"
        assert data["progress"] == 60 # Based on mapping in routes.py

def test_history_endpoint(client):
    """
    Test 3: Create a dummy history file and verify /api/v1/history returns it.
    """
    dummy_history = {
        "sessions": [
            {
                "id": "hist_1",
                "timestamp": "2023-01-01T00:00:00",
                "title": "Old Session",
                "topic": "General",
                "status": "completed",
                "mode": "general_doc",
                "mode_name": "General Documentation"
            }
        ]
    }
    
    # We can mock the StorageService.get_history method
    with patch("app.services.storage_service.StorageService.get_history") as mock_get_history:
        mock_get_history.return_value = dummy_history["sessions"]
        
        response = client.get("/api/v1/history")
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "hist_1"
        assert data["sessions"][0]["title"] == "Old Session"
