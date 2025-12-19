"""Pytest configuration for DevLens AI tests"""

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
import json

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


@pytest.fixture
def client():
    """Create FastAPI test client"""
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def mock_genai():
    """Mock Google GenerativeAI"""
    with patch('google.generativeai.GenerativeModel') as mock:
        yield mock


@pytest.fixture
def mock_flash_response():
    """Mock Gemini Flash audio analysis response"""
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "relevant_segments": [
            {"start": 10.0, "end": 20.0, "reason": "Technical discussion"},
            {"start": 30.0, "end": 40.0, "reason": "Bug analysis"}
        ],
        "technical_percentage": 50.0
    })
    return mock_resp


@pytest.fixture
def mock_pro_response():
    """Mock Gemini Pro documentation response"""
    mock_resp = MagicMock()
    mock_resp.text = "# Generated Documentation\n\nThis is a mock doc."
    return mock_resp


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    yield
    
    # Reset ai_generator singleton
    try:
        import app.services.ai_generator as ai_mod
        ai_mod._generator = None
    except (ImportError, AttributeError):
        pass
    
    # Reset calendar_watcher singleton
    try:
        import app.services.calendar_service as cal_mod
        cal_mod._calendar_watcher = None
        cal_mod._scheduler_running = False
    except (ImportError, AttributeError):
        pass
    
    # Reset notification_service singleton
    try:
        import app.services.notification_service as notif_mod
        notif_mod._notification_service = None
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def mock_settings():
    """Provide mock settings for tests"""
    settings = MagicMock()
    settings.gemini_api_key = "test_gemini_key"
    settings.upload_dir = "./test_uploads"
    settings.frame_interval = 5
    settings.max_video_length = 900
    return settings

