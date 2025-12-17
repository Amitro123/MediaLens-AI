import pytest
import os
import json
from pathlib import Path

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock required environment variables for all history tests"""
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    monkeypatch.setenv("GROQ_API_KEY", "test_key")

@pytest.fixture
def clean_storage(monkeypatch):
    """Ensure a clean history.json for testing"""
    from app.services.storage_service import get_storage_service
    
    # Mock settings.upload_dir for the storage service
    from app.core.config import settings
    monkeypatch.setattr(settings, "upload_dir", "./test_uploads")
    
    storage = get_storage_service()
    history_file = storage.history_file
    
    # Cleanup if exists
    if history_file.exists():
        history_file.unlink()
        
    # Re-init (creates empty file)
    storage.__init__("./data_test")
    
    yield storage
    
    # Cleanup test files
    if history_file.exists():
        history_file.unlink()
    if Path("./data_test").exists():
        import shutil
        shutil.rmtree("./data_test", ignore_errors=True)

def test_storage_service_add_session(clean_storage, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "upload_dir", "./test_uploads")
    
    storage = clean_storage
    session_id = "test_session_123"
    metadata = {
        "title": "Test Meeting",
        "topic": "Testing",
        "status": "completed",
        "documentation": "# Test Content"
    }
    
    storage.add_session(session_id, metadata)
    
    history = storage.get_history()
    assert len(history) == 1
    assert history[0]["id"] == session_id
    assert history[0]["title"] == "Test Meeting"
    
    # Check disk artifact
    upload_path = Path(settings.upload_dir) / session_id / "documentation.md"
    assert upload_path.exists()
    assert upload_path.read_text() == "# Test Content"

def test_api_history_endpoint(clean_storage, client):
    # Add a session via storage
    clean_storage.add_session("api_test_id", {"title": "API Test"})
    
    response = client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert len(data["sessions"]) >= 1
    assert data["sessions"][0]["id"] == "api_test_id"

def test_api_persistent_result_loading(clean_storage, client):
    session_id = "persistence_test_id"
    doc_content = "# Persisted Doc"
    
    # Manually save to disk as if it was processed before
    clean_storage.add_session(session_id, {
        "title": "Persistence Test",
        "documentation": doc_content,
        "mode": "general_doc",
        "mode_name": "General Documentation"
    })
    
    # Now try to get result from API
    response = client.get(f"/api/v1/result/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == session_id
    assert data["documentation"] == doc_content
