"""Unit tests for Fast STT Service"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestFastSttService:
    """Test the Fast STT service with mocks"""

    @patch("app.services.stt_fast_service.WhisperModel")
    def test_transcribe_video_success(self, mock_whisper):
        from app.services.stt_fast_service import FastSttService
        
        # Setup mock model
        mock_model = mock_whisper.return_value
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "Hello world"
        mock_segment.avg_logprob = 0.9
        mock_model.transcribe.return_value = ([mock_segment], MagicMock(duration=5.0))
        
        service = FastSttService()
        result = service.transcribe_video(str(Path("test.wav")))
        
        # transcribe_video returns SttResult object
        assert hasattr(result, 'segments')
        assert len(result.segments) == 1
        assert result.segments[0]["text"] == "Hello world"
        assert result.model_used.startswith("faster_whisper")

    @patch("app.services.stt_fast_service.WhisperModel", side_effect=Exception("Model load failed"))
    def test_transcribe_video_fallback(self, mock_whisper_error):
        from app.services.stt_fast_service import FastSttService
        
        service = FastSttService()
        result = service.transcribe_video(str(Path("test.wav")))
        
        # Should fallback to Gemini
        assert result.model_used == "gemini_fallback"
        assert len(result.segments) == 0

    def test_is_hebrew_context(self):
        from app.services.stt_fast_service import FastSttService
        service = FastSttService(enabled=False)  # Don't load model for this test
        
        # Test filename-based detection
        assert service.is_hebrew_context("test_ivrit.wav") is True
        assert service.is_hebrew_context("meeting_hebrew.wav") is True
        assert service.is_hebrew_context("normal_meeting.wav") is False
        
        # Test metadata-based detection
        assert service.is_hebrew_context("test.wav", {"language": "he"}) is True
        assert service.is_hebrew_context("test.wav", {"keywords": ["Israel"]}) is True
        assert service.is_hebrew_context("test.wav", {"language": "en"}) is False

