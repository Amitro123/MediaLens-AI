"""
Tests for HebrishSTTService - Hebrew + English tech term transcription.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from app.services.stt_hebrish_service import (
    HebrishSTTService,
    HebrishResult,
    get_hebrish_stt_service,
    reset_hebrish_stt_service,
    TECH_VOCAB_PROMPT
)


# =============================================================================
# HebrishResult Tests
# =============================================================================

class TestHebrishResult:
    """Test HebrishResult dataclass"""
    
    def test_empty_result(self):
        """Test empty result properties"""
        result = HebrishResult()
        assert result.segment_count == 0
        assert result.total_duration == 0.0
        assert result.model_used == "ivrit-ai/faster-whisper-v2-d4"
    
    def test_with_segments(self):
        """Test result with segments"""
        result = HebrishResult(
            segments=[
                {"start": 0.0, "end": 5.0, "text": "תעשה deploy ל-production"},
                {"start": 5.0, "end": 10.0, "text": "ותבדוק את ה-logs"}
            ],
            processing_time_ms=200.0,
            model_used="ivrit-ai/faster-whisper-v2-d4"
        )
        assert result.segment_count == 2
        assert result.total_duration == 10.0
        assert result.processing_time_ms == 200.0


# =============================================================================
# HebrishSTTService Tests
# =============================================================================

class TestHebrishSTTService:
    """Test HebrishSTTService class"""
    
    @patch("app.services.stt_hebrish_service.HebrishSTTService._load_model")
    def test_init_loads_model(self, mock_load):
        """Test service attempts to load model on init"""
        reset_hebrish_stt_service()
        service = HebrishSTTService()
        mock_load.assert_called_once()
    
    @patch("app.services.stt_hebrish_service.HebrishSTTService._load_model")
    def test_not_available_when_model_none(self, mock_load):
        """Test is_available returns False when model is None"""
        reset_hebrish_stt_service()
        service = HebrishSTTService()
        service.model = None
        assert not service.is_available
    
    @patch("app.services.stt_hebrish_service.HebrishSTTService._load_model")
    def test_transcribe_returns_empty_when_unavailable(self, mock_load):
        """Test transcription returns empty result when model unavailable"""
        reset_hebrish_stt_service()
        service = HebrishSTTService()
        service.model = None
        
        result = service.transcribe("/fake/path.wav")
        assert result.segments == []
        assert result.model_used == "unavailable"
    
    @patch("app.services.stt_hebrish_service.HebrishSTTService._load_model")
    def test_health_status_unavailable(self, mock_load):
        """Test health status when unavailable"""
        reset_hebrish_stt_service()
        service = HebrishSTTService()
        service.model = None
        service._model_load_error = "Test error"
        
        status = service.get_health_status()
        assert status["available"] == False
        assert status["error"] == "Test error"
        assert "ivrit-ai" in status["model"]


# =============================================================================
# Integration Tests (with mocked model)
# =============================================================================

class TestHebrishSTTServiceWithMockedModel:
    """Test HebrishSTTService with mocked Whisper model"""
    
    @patch("app.services.stt_hebrish_service.HebrishSTTService._load_model")
    def test_transcribe_success(self, mock_load):
        """Test successful transcription with mocked model"""
        reset_hebrish_stt_service()
        service = HebrishSTTService()
        
        # Mock the model and transcription
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "תעשה deploy ל-production"
        mock_segment.avg_logprob = -0.3
        
        mock_info = MagicMock()
        mock_info.duration = 5.0
        
        service.model = MagicMock()
        service.model.transcribe.return_value = ([mock_segment], mock_info)
        
        result = service.transcribe("/fake/path.wav")
        
        assert result.model_used == "ivrit-ai/faster-whisper-v2-d4"
        assert result.segment_count == 1
        assert result.segments[0]["text"] == "תעשה deploy ל-production"
    
    @patch("app.services.stt_hebrish_service.HebrishSTTService._load_model")
    def test_transcribe_uses_tech_vocab_prompt(self, mock_load):
        """Test that transcription uses tech vocabulary prompt"""
        reset_hebrish_stt_service()
        service = HebrishSTTService()
        
        service.model = MagicMock()
        service.model.transcribe.return_value = ([], MagicMock(duration=0))
        
        service.transcribe("/fake/path.wav")
        
        # Verify initial_prompt was passed with tech vocab
        call_kwargs = service.model.transcribe.call_args[1]
        assert "initial_prompt" in call_kwargs
        assert "deploy" in call_kwargs["initial_prompt"]
        assert "kubernetes" in call_kwargs["initial_prompt"]


# =============================================================================
# Tech Vocab Prompt Tests
# =============================================================================

class TestTechVocabPrompt:
    """Test tech vocabulary prompt content"""
    
    def test_contains_common_tech_terms(self):
        """Test prompt contains common tech terms"""
        expected_terms = [
            "deploy", "production", "logs", "API", "JSON",
            "React", "kubernetes", "commit", "PR", "merge"
        ]
        for term in expected_terms:
            assert term in TECH_VOCAB_PROMPT, f"Missing term: {term}"
    
    def test_contains_backend_terms(self):
        """Test prompt contains backend development terms"""
        expected_terms = ["database", "server", "endpoint", "docker", "redis"]
        for term in expected_terms:
            assert term in TECH_VOCAB_PROMPT, f"Missing term: {term}"


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingleton:
    """Test singleton pattern"""
    
    def test_reset_clears_instance(self):
        """Test reset clears singleton"""
        reset_hebrish_stt_service()
        
        from app.services import stt_hebrish_service
        stt_hebrish_service._hebrish_stt_service = MagicMock()
        
        reset_hebrish_stt_service()
        
        assert stt_hebrish_service._hebrish_stt_service is None
