"""
Tests for FastSttService - local Whisper-based transcription.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from app.services.stt_fast_service import (
    FastSttService,
    SttResult,
    get_fast_stt_service,
    reset_fast_stt_service
)


# =============================================================================
# SttResult Tests
# =============================================================================

class TestSttResult:
    """Test SttResult dataclass"""
    
    def test_empty_result(self):
        """Test empty result properties"""
        result = SttResult()
        assert result.segment_count == 0
        assert result.total_duration == 0.0
        assert result.model_used == "none"
    
    def test_with_segments(self):
        """Test result with segments"""
        result = SttResult(
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello world"},
                {"start": 5.0, "end": 10.0, "text": "How are you"}
            ],
            processing_time_ms=150.0,
            model_used="faster_whisper_small"
        )
        assert result.segment_count == 2
        assert result.total_duration == 10.0
        assert result.processing_time_ms == 150.0
    
    def test_get_text_summary(self):
        """Test summary generation"""
        result = SttResult(
            segments=[
                {"start": 0.0, "end": 5.0, "text": "Hello world"},
                {"start": 5.0, "end": 10.0, "text": "How are you"}
            ]
        )
        summary = result.get_text_summary()
        assert "[0.0s] Hello world" in summary
        assert "[5.0s] How are you" in summary
    
    def test_get_text_summary_truncation(self):
        """Test summary truncation for long transcripts"""
        # Create many segments
        segments = [
            {"start": i * 5.0, "end": (i + 1) * 5.0, "text": f"Segment {i} " * 20}
            for i in range(50)
        ]
        result = SttResult(segments=segments)
        summary = result.get_text_summary(max_tokens=100)
        # Should truncate and add ellipsis
        assert "..." in summary or len(summary) < 1000


# =============================================================================
# FastSttService Tests
# =============================================================================

class TestFastSttService:
    """Test FastSttService class"""
    
    def test_init_disabled(self):
        """Test service initializes when disabled"""
        reset_fast_stt_service()
        service = FastSttService(enabled=False)
        assert not service.enabled
        assert not service.is_available
        assert service.model is None
    
    @patch("app.services.stt_fast_service.FastSttService._load_model")
    def test_init_enabled_no_model(self, mock_load):
        """Test service when model fails to load"""
        reset_fast_stt_service()
        service = FastSttService(enabled=True)
        service.model = None
        assert service.enabled
        assert not service.is_available
    
    def test_transcribe_disabled_returns_fallback(self):
        """Test transcription returns fallback when disabled"""
        reset_fast_stt_service()
        service = FastSttService(enabled=False)
        result = service.transcribe_video("/fake/path.wav")
        assert result.model_used == "gemini_fallback"
        assert result.segments == []
    
    def test_transcribe_no_model_returns_fallback(self):
        """Test transcription returns fallback when model unavailable"""
        reset_fast_stt_service()
        service = FastSttService(enabled=True)
        service.model = None  # Force no model
        result = service.transcribe_video("/fake/path.wav")
        assert result.model_used == "gemini_fallback"
    
    def test_health_status_disabled(self):
        """Test health status when disabled"""
        reset_fast_stt_service()
        service = FastSttService(enabled=False)
        status = service.get_health_status()
        assert status["enabled"] == False
        assert status["available"] == False
    
    def test_health_status_enabled_no_model(self):
        """Test health status when model fails"""
        reset_fast_stt_service()
        service = FastSttService(enabled=True)
        service.model = None
        service._model_load_error = "Test error"
        status = service.get_health_status()
        assert status["enabled"] == True
        assert status["available"] == False
        assert status["error"] == "Test error"


# =============================================================================
# Integration Tests (with mocked model)
# =============================================================================

class TestFastSttServiceWithMockedModel:
    """Test FastSttService with mocked Whisper model"""
    
    @patch("app.services.stt_fast_service.FastSttService._load_model")
    def test_transcribe_success(self, mock_load):
        """Test successful transcription with mocked model"""
        reset_fast_stt_service()
        service = FastSttService(enabled=True)
        
        # Mock the model and transcription
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "Hello world"
        mock_segment.avg_logprob = -0.5
        
        mock_info = MagicMock()
        mock_info.duration = 5.0
        
        service.model = MagicMock()
        service.model.transcribe.return_value = ([mock_segment], mock_info)
        
        result = service.transcribe_video("/fake/path.wav")
        
        assert result.model_used == "faster_whisper_small"
        assert result.segment_count == 1
        assert result.segments[0]["text"] == "Hello world"
        assert result.processing_time_ms >= 0  # Can be 0 for mocked fast execution


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingleton:
    """Test singleton pattern"""
    
    def test_reset_clears_instance(self):
        """Test reset clears singleton"""
        reset_fast_stt_service()
        
        # Create directly without the getter to avoid settings import
        from app.services import stt_fast_service
        stt_fast_service._fast_stt_service = FastSttService(enabled=False)
        
        service1 = stt_fast_service._fast_stt_service
        reset_fast_stt_service()
        
        assert stt_fast_service._fast_stt_service is None
