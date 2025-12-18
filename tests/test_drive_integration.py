
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# TestClient is provided by conftest.py's client fixture

# Mock data
MOCK_FILE_ID = "12345-abcde"
MOCK_DRIVE_URL = "https://drive.google.com/file/d/12345-abcde/view?usp=sharing"
MOCK_SESSION_ID = None  # Will be set in setup

@pytest.fixture
def mock_calendar_service():
    with patch("app.services.calendar_service.get_calendar_watcher") as mock:
        yield mock

@pytest.fixture
def mock_drive_connector():
    with patch("app.services.drive_connector.DriveConnector") as MockConnector:
        # Create an instance mock
        instance = MockConnector.return_value
        instance.extract_file_id.return_value = MOCK_FILE_ID
        instance.download_file.return_value = None # Just return None or path
        yield instance

@pytest.fixture
def mock_video_processor():
    # Patch video processing functions in the new video_pipeline module
    with patch("app.services.video_pipeline.extract_audio") as mock_audio, \
         patch("app.services.video_pipeline.extract_frames") as mock_frames, \
         patch("app.services.video_pipeline.get_video_duration") as mock_duration:
        
        mock_duration.return_value = 60.0 # 60 seconds
        mock_audio.return_value = "mock_audio.mp3"
        mock_frames.return_value = ["frame1.jpg", "frame2.jpg"]
        yield mock_audio, mock_frames, mock_duration

@pytest.fixture
def mock_ai_generator():
    with patch("app.services.video_pipeline.get_generator") as mock_get_gen:
        generator = MagicMock()
        # Mock analyze_audio_relevance
        generator.analyze_audio_relevance.return_value = [
            {"start": 10, "end": 20},
            {"start": 40, "end": 50}
        ]
        # Mock generate_documentation
        generator.generate_documentation.return_value = "# Mock Documentation\n\nGenerated from Drive upload."
        
        mock_get_gen.return_value = generator
        yield generator

@pytest.fixture
def mock_settings():
    # Patch settings in both routes.py and video_pipeline.py
    with patch("app.api.routes.settings") as mock_settings_routes, \
         patch("app.services.video_pipeline.settings") as mock_settings_pipeline:
        mock_settings_routes.get_upload_path.return_value = Path("/tmp/uploads")
        mock_settings_routes.max_video_length = 300
        mock_settings_routes.frame_interval = 5
        mock_settings_pipeline.max_video_length = 300
        mock_settings_pipeline.frame_interval = 5
        yield mock_settings_routes



def test_drive_upload_success(
    client,
    mock_calendar_service, 
    mock_drive_connector, 
    mock_video_processor, 
    mock_ai_generator
):
    """Test successful Drive upload flow"""
    
    # Setup Session
    mock_calendar = mock_calendar_service.return_value
    mock_session = MagicMock()
    mock_session.id = "session-123"
    mock_session.title = "Test Session"
    mock_session.attendees = ["alice@example.com"]
    mock_session.context_keywords = ["feature", "test"]
    mock_session.suggested_mode = "feature_spec"
    
    # Setup get_session behavior
    mock_calendar.get_session.return_value = mock_session
    
    # Configure Drive Connector Mock
    mock_drive_connector.extract_file_id.return_value = MOCK_FILE_ID
    
    # Payload
    payload = {
        "url": MOCK_DRIVE_URL,
        "session_id": "session-123"
    }
    
    # Execute Request
    # We also need to patch prompt_loader to avoid file I/O errors
    with patch("app.api.routes.get_prompt_loader") as mock_loader_get:
        mock_loader = MagicMock()
        mock_loader.load_prompt.return_value.name = "Test Mode"
        mock_loader_get.return_value = mock_loader
        
        # Also need to mock Path.mkdir and open because routes opens file/dir
        # And patch storage service in video_pipeline
        with patch("pathlib.Path.mkdir"), \
             patch("builtins.open", create=True), \
             patch("app.services.video_pipeline.get_storage_service"):
             response = client.post("/api/v1/upload/drive", json=payload)

        # Assertions
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.json()}")
        assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "Mock Documentation" in data["result"]
    assert data["task_id"] == "session-123"
    
    # Verify Drive interactions
    mock_drive_connector.extract_file_id.assert_called_with(MOCK_DRIVE_URL)
    # Verify download was called (path arguments are tricky to assert exactly with Path objects in mocks)
    assert mock_drive_connector.download_file.called

    # Verify Calendar Status Updates
    mock_calendar.update_session_status.assert_any_call("session-123", "downloading_from_drive")
    mock_calendar.update_session_status.assert_any_call("session-123", "processing")
    # Last call should be 'completed'
    assert mock_calendar.update_session_status.call_args_list[-1][0][1] == "completed"

def test_drive_upload_invalid_url(client, mock_calendar_service, mock_drive_connector):
    """Test invalid Drive URL handling"""
    mock_calendar = mock_calendar_service.return_value
    mock_calendar.get_session.return_value = MagicMock()
    
    # Connector returns None for ID
    mock_drive_connector.extract_file_id.return_value = None
    
    payload = {
        "url": "https://invalid-url.com",
        "session_id": "session-123"
    }
    
    response = client.post("/api/v1/upload/drive", json=payload)
    
    assert response.status_code == 400
    assert "Invalid Google Drive URL" in response.json()["detail"]

def test_drive_upload_session_not_found(client, mock_calendar_service):
    """Test upload with invalid session ID"""
    mock_calendar = mock_calendar_service.return_value
    mock_calendar.get_session.return_value = None
    
    payload = {
        "url": MOCK_DRIVE_URL,
        "session_id": "non-existent-session"
    }
    
    response = client.post("/api/v1/upload/drive", json=payload)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
