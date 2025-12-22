"""
E2E Pipeline Tests - Full video processing flow tests.

Tests the complete pipeline from video upload to documentation generation,
including STT, Gemini analysis, and metrics logging.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import time


# =============================================================================
# Test: Full Pipeline with Sample Video (via API)
# =============================================================================

@patch("app.api.routes.get_devlens_agent")
def test_full_pipeline_sample_video(mock_agent, client, tmp_path):
    """
    E2E Test: Full pipeline via API generates documentation.
    
    Asserts:
    - Upload endpoint returns success
    - Documentation is in response
    """
    from app.services.agent_orchestrator import DevLensResult
    
    # Mock agent result
    mock_agent_instance = MagicMock()
    mock_agent.return_value = mock_agent_instance
    
    async def mock_generate(*args, **kwargs):
        return DevLensResult(
            session_id="e2e_test_001",
            status="completed",
            documentation="# E2E Generated Docs\n\nTest content.",
            mode="general_doc",
            mode_name="General Documentation",
            project_name="E2E Test"
        )
    mock_agent_instance.generate_documentation = mock_generate
    
    # Create dummy video
    import io
    video_content = io.BytesIO(b"dummy mp4 content")
    
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.mp4", video_content, "video/mp4")},
        data={"project_name": "E2E Test", "mode": "general_doc"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "E2E Generated Docs" in data["result"]


# =============================================================================
# Test: STT Fallback When Whisper Unavailable
# =============================================================================

def test_stt_fallback_when_whisper_fails():
    """
    E2E Test: When faster-whisper fails to load, service falls back to Gemini.
    
    Asserts:
    - Service initializes without crashing
    - Fallback result indicates gemini_fallback model used
    """
    from app.services.stt_fast_service import FastSttService, reset_fast_stt_service
    
    reset_fast_stt_service()
    
    # Create service with mocked failing import
    with patch("app.services.stt_fast_service.FastSttService._load_model") as mock_load:
        # Simulate model load failure
        service = FastSttService(enabled=True)
        service.model = None  # Force fallback path
        service._model_load_error = "Test: Model unavailable"
        
        # Attempt transcription
        result = service.transcribe_video("/fake/audio.wav")
        
        # Assertions
        assert result.model_used == "gemini_fallback"
        assert result.segments == []
        assert not service.is_available


# =============================================================================
# Test: Long Video Configuration Check
# =============================================================================

def test_long_video_config():
    """
    E2E Test: Config supports 15-minute videos.
    
    Asserts:
    - Max video length setting allows 15 minutes
    """
    from app.core.config import settings
    
    # 15 minutes = 900 seconds
    assert settings.max_video_length >= 900, \
        f"Max video length {settings.max_video_length}s is less than 15 minutes"


# =============================================================================
# Test: Metrics Logging
# =============================================================================

def test_stt_metrics_logging():
    """
    Test: STT service returns proper metrics.
    """
    from app.services.stt_fast_service import SttResult, reset_fast_stt_service
    
    reset_fast_stt_service()
    
    # Create result with metrics
    result = SttResult(
        segments=[{"start": 0.0, "end": 5.0, "text": "Hello"}],
        processing_time_ms=1234.5,
        model_used="faster_whisper_small"
    )
    
    # Verify metrics are accessible
    assert result.segment_count == 1
    assert result.processing_time_ms == 1234.5
    assert result.model_used == "faster_whisper_small"
    assert result.total_duration == 5.0


# =============================================================================
# Test: Agent Integration
# =============================================================================

def test_devlens_agent_available():
    """
    Test: DevLensAgent is properly instantiated.
    """
    from app.services.agent_orchestrator import get_devlens_agent, DevLensAgent
    
    agent = get_devlens_agent()
    assert agent is not None
    assert isinstance(agent, DevLensAgent)
