"""Unit tests for Fast STT Service"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Create a mock for faster_whisper module
mock_faster_whisper = MagicMock()
mock_whisper_model = MagicMock()
mock_faster_whisper.WhisperModel = mock_whisper_model

class TestFastSttService:
    """Test the Fast STT service with mocks"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset singleton before and after tests"""
        from app.services.stt_fast_service import reset_fast_stt_service
        reset_fast_stt_service()
        yield
        reset_fast_stt_service()

    def test_transcribe_video_success(self):
        # Patch the module in sys.modules so 'from faster_whisper import WhisperModel' works
        with patch.dict(sys.modules, {"faster_whisper": mock_faster_whisper}):
            from app.services.stt_fast_service import FastSttService
            
            # Setup mock model instance
            mock_model_instance = mock_whisper_model.return_value
            mock_segment = MagicMock()
            mock_segment.start = 0.0
            mock_segment.end = 5.0
            mock_segment.text = "Hello world"
            mock_segment.avg_logprob = 0.9
            mock_model_instance.transcribe.return_value = ([mock_segment], MagicMock(duration=5.0))
            
            service = FastSttService(enabled=True)
            result = service.transcribe_video(str(Path("test.wav")))
            
            # transcribe_video returns SttResult object
            assert hasattr(result, 'segments')
            assert len(result.segments) == 1
            assert result.segments[0]["text"] == "Hello world"
            assert result.model_used.startswith("faster_whisper")

    def test_transcribe_video_fallback(self):
        # Mock WhisperModel raising exception on init
        mock_error_whisper = MagicMock()
        mock_error_class = MagicMock(side_effect=Exception("Model load failed"))
        mock_error_whisper.WhisperModel = mock_error_class

        with patch.dict(sys.modules, {"faster_whisper": mock_error_whisper}):
            from app.services.stt_fast_service import FastSttService
            
            service = FastSttService(enabled=True)
            result = service.transcribe_video(str(Path("test.wav")))
            
            # Should fallback to Gemini
            assert result.model_used == "gemini_fallback"
            assert len(result.segments) == 0

    def test_is_hebrew_context(self):
        from app.services.stt_fast_service import FastSttService
        # Initialize with enabled=False to avoid loading model
        service = FastSttService(enabled=False)
        
        # Test filename-based detection
        assert service.is_hebrew_context("test_ivrit.wav") is True
        assert service.is_hebrew_context("meeting_hebrew.wav") is True
        assert service.is_hebrew_context("normal_meeting.wav") is False
        
        # Test metadata-based detection
        assert service.is_hebrew_context("test.wav", {"language": "he"}) is True
        assert service.is_hebrew_context("test.wav", {"keywords": ["Israel"]}) is True
        assert service.is_hebrew_context("test.wav", {"language": "en"}) is False

