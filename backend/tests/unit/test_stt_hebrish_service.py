"""Unit tests for STT Hebrish Service"""
import pytest
from unittest.mock import patch, MagicMock
import threading


class TestHebrishSTTServiceImports:
    """Test basic imports and module structure"""

    def test_module_import(self):
        """Test that module can be imported"""
        from app.services import stt_hebrish_service
        assert stt_hebrish_service is not None

    def test_service_class_exists(self):
        """Test HebrishSTTService class exists"""
        from app.services.stt_hebrish_service import HebrishSTTService
        assert HebrishSTTService is not None


class TestHebrishSTTServiceSingleton:
    """Test the Hebrish STT service singleton pattern"""

    def test_singleton_pattern(self):
        """Test that get_hebrish_stt_service returns singleton"""
        from app.services.stt_hebrish_service import (
            get_hebrish_stt_service,
            reset_hebrish_stt_service
        )
        
        reset_hebrish_stt_service()  # Clean state
        
        service1 = get_hebrish_stt_service()
        service2 = get_hebrish_stt_service()
        
        assert service1 is service2
        
        reset_hebrish_stt_service()  # Cleanup

    def test_reset_clears_singleton(self):
        """Test that reset clears the singleton instance"""
        from app.services.stt_hebrish_service import (
            get_hebrish_stt_service,
            reset_hebrish_stt_service
        )
        from app.services import stt_hebrish_service
        
        reset_hebrish_stt_service()
        _ = get_hebrish_stt_service()
        
        reset_hebrish_stt_service()
        
        # After reset, module-level variable should be None
        assert stt_hebrish_service._hebrish_stt_service is None


class TestHebrishSTTServiceThreadSafety:
    """Test thread-safe singleton initialization"""

    def test_thread_safety(self):
        """Test thread-safe singleton initialization"""
        from app.services.stt_hebrish_service import (
            get_hebrish_stt_service,
            reset_hebrish_stt_service
        )
        
        reset_hebrish_stt_service()
        instances = []
        errors = []
        
        def get_instance():
            try:
                instance = get_hebrish_stt_service()
                instances.append(instance)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads to get the service concurrently
        threads = [threading.Thread(target=get_instance) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All instances should be the same object
        assert len(errors) == 0
        assert len(instances) == 5
        assert all(inst is instances[0] for inst in instances)
        
        reset_hebrish_stt_service()


class TestHebrishSTTServiceHealth:
    """Test health status functionality"""

    def test_health_status_structure(self):
        """Test health status returns correct structure"""
        from app.services.stt_hebrish_service import get_hebrish_stt_service, reset_hebrish_stt_service
        
        reset_hebrish_stt_service()
        service = get_hebrish_stt_service()
        
        status = service.get_health_status()
        
        assert "available" in status
        assert "device" in status
        assert "model" in status
        assert isinstance(status["available"], bool)
        
        reset_hebrish_stt_service()


class TestTechVocab:
    """Test tech vocabulary loading"""

    def test_tech_vocab_prompt_loaded(self):
        """Test that tech vocabulary prompt function exists"""
        from app.services.stt_hebrish_service import _load_tech_prompt
        
        prompt = _load_tech_prompt()
        
        assert prompt is not None
        assert len(prompt) > 0
        # Should contain some tech terms
        assert any(term in prompt for term in ["API", "deploy", "docker", "React"])
