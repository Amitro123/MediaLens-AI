import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.api.routes import router
from fastapi import FastAPI
import uuid

# Create a minimal app for testing the router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_get_active_session_none():
    """Test when no sessions are active"""
    with patch("app.services.calendar_service.get_calendar_watcher") as mock_get_watcher:
        mock_watcher = MagicMock()
        mock_watcher.get_draft_sessions.return_value = []
        mock_get_watcher.return_value = mock_watcher
        
        # Ensure task_results is empty (resetting if necessary)
        with patch("app.api.routes.task_results", {}):
            response = client.get("/api/v1/active-session")
            assert response.status_code == 200
            assert response.json() is None

def test_get_active_session_calendar():
    """Test when a calendar session is active"""
    session_id = str(uuid.uuid4())
    mock_session = MagicMock()
    mock_session.session_id = session_id
    mock_session.status = "processing"
    mock_session.title = "Test Meeting"
    mock_session.suggested_mode = "bug_report"
    
    with patch("app.services.calendar_service.get_calendar_watcher") as mock_get_watcher:
        mock_watcher = MagicMock()
        mock_watcher.get_draft_sessions.return_value = [mock_session]
        mock_get_watcher.return_value = mock_watcher
        
        with patch("app.api.routes.task_results", {}):
            response = client.get("/api/v1/active-session")
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["status"] == "processing"
            assert data["title"] == "Test Meeting"

def test_get_active_session_manual():
    """Test when a manual upload is active"""
    session_id = "manual_123"
    active_manual = {
        "status": "processing",
        "project_name": "Manual Project",
        "mode": "general_doc"
    }
    
    with patch("app.services.calendar_service.get_calendar_watcher") as mock_get_watcher:
        mock_watcher = MagicMock()
        mock_watcher.get_draft_sessions.return_value = []
        mock_get_watcher.return_value = mock_watcher
        
        with patch("app.api.routes.task_results", {session_id: active_manual}):
            response = client.get("/api/v1/active-session")
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["status"] == "processing"
            assert data["title"] == "Manual Project"

def test_get_status_recovery():
    """Test that get_status works for calendar sessions"""
    session_id = "cal_session_123"
    mock_session = MagicMock()
    mock_session.status = "downloading_from_drive"
    
    with patch("app.services.calendar_service.get_calendar_watcher") as mock_get_watcher:
        mock_watcher = MagicMock()
        mock_watcher.get_session.return_value = mock_session
        mock_get_watcher.return_value = mock_watcher
        
        with patch("app.api.routes.task_results", {}):
            response = client.get(f"/api/v1/status/{session_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "downloading_from_drive"
            assert response.json()["progress"] == 30
