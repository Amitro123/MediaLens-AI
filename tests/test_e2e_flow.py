import pytest
from unittest.mock import patch, MagicMock
from app.services.calendar_service import get_calendar_watcher

# Test Case 1: Verify GET /drafts returns events
def test_calendar_flow(client):
    response = client.get("/api/v1/sessions/drafts")
    assert response.status_code == 200
    drafts = response.json()
    assert isinstance(drafts, list)
    assert len(drafts) > 0
    assert "id" in drafts[0]
    assert "status" in drafts[0]

# Test Case 2: Verify calling /prep changes status to ready
def test_prep_context(client):
    # First get a draft
    drafts = client.get("/api/v1/sessions/drafts").json()
    session_id = drafts[0]["id"]
    
    # Prep it
    response = client.post(f"/api/v1/sessions/{session_id}/prep")
    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_upload"
    
    # Verify status persisted
    calendar = get_calendar_watcher()
    session = calendar.get_session(session_id)
    assert session.status == "ready_for_upload"

# Test Case 3: Smart Upload Flow (Mocked AI) - Dual-Stream Pipeline
@patch('app.services.ai_generator.genai')
@patch('app.services.video_processor.create_low_fps_proxy')
@patch('app.services.video_pipeline.extract_frames')
@patch('app.services.video_pipeline.get_video_duration')
@patch('app.api.routes.get_prompt_loader')
@patch('app.services.video_pipeline.get_storage_service')
def test_smart_upload(mock_storage, mock_get_loader, mock_get_duration, mock_extract_frames, mock_create_proxy, mock_genai, client, mock_flash_response, mock_pro_response):
    # Setup Mocks for Dual-Stream Pipeline
    mock_create_proxy.return_value = "dummy_proxy_1fps.mp4"
    # mock_extract_frames checks return value, but routes.py calls it with timestamps
    mock_extract_frames.return_value = ["frame1.jpg", "frame2.jpg"]
    mock_get_duration.return_value = 120.0
    
    # Mock PromptLoader response
    mock_loader_instance = MagicMock()
    mock_loader_instance.load_prompt.return_value = MagicMock(
        system_instruction="Simulated system prompt",
        name="Test Mode"
    )
    mock_get_loader.return_value = mock_loader_instance
    
    # Mock the DocumentationGenerator internal models
    with patch('app.services.ai_generator.DocumentationGenerator._analyze_multimodal_fast') as mock_analyze:
        with patch('app.services.ai_generator.DocumentationGenerator.generate_documentation') as mock_generate:
            mock_analyze.return_value = mock_flash_response
            mock_generate.return_value = "# Mock Doc"
            
            # 1. Get a session and prep it
            drafts = client.get("/api/v1/sessions/drafts").json()
            session_id = drafts[0]["id"]
            client.post(f"/api/v1/sessions/{session_id}/prep")
            
            # 2. Upload video
            files = {'file': ('video.mp4', b'dummy content', 'video/mp4')}
            response = client.post(
                f"/api/v1/upload/{session_id}", 
                files=files
            )
            
            # 3. Verify assertions
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            
            # Verify Mock Calls for Dual-Stream Pipeline
            # 1. Proxy video was created for fast semantic analysis
            # Note: We're not mocking create_low_fps_proxy, so it's actually called via run_in_threadpool
            
            # 2. Multimodal analysis was called on the proxy (not audio extraction)
            mock_analyze.assert_called_once()
            
            # 3. Frames were extracted from the original high-quality video
            # at the timestamps identified by the AI analysis
            mock_extract_frames.assert_called_once()
            
            # 4. Doc generation called
            mock_generate.assert_called_once()
