"""Unit tests for STT Hebrish Service"""
import pytest
import sys
import threading
from unittest.mock import patch, MagicMock, call
# Mock faster_whisper before importing service
from unittest.mock import MagicMock
sys.modules["faster_whisper"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["torch"].cuda.is_available.return_value = False

from app.services import stt_hebrish_service

@pytest.fixture
def mock_whisper_model():
    # Since we mocked faster_whisper in sys.modules, accessing it here gives us the mock
    import faster_whisper
    return faster_whisper.WhisperModel

@pytest.fixture
def mock_session_manager():
    with patch("app.services.session_manager.get_session_manager") as mock:
        yield mock

class TestHebrishSTTServiceImports:
    """Test basic imports and module structure"""

    def test_module_import(self):
        """Test that module can be imported"""
        assert stt_hebrish_service is not None

    def test_service_class_exists(self):
        """Test HebrishSTTService class exists"""
        assert stt_hebrish_service.HebrishSTTService is not None


class TestHebrishSTTServiceSingleton:
    """Test the Hebrish STT service singleton pattern"""

    def test_singleton_pattern(self, mock_whisper_model):
        """Test that get_hebrish_stt_service returns singleton"""
        stt_hebrish_service.reset_hebrish_stt_service()  # Clean state
        
        service1 = stt_hebrish_service.get_hebrish_stt_service()
        service2 = stt_hebrish_service.get_hebrish_stt_service()
        
        assert service1 is service2
        
        stt_hebrish_service.reset_hebrish_stt_service()  # Cleanup

    def test_reset_clears_singleton(self, mock_whisper_model):
        """Test that reset clears the singleton instance"""
        stt_hebrish_service.reset_hebrish_stt_service()
        _ = stt_hebrish_service.get_hebrish_stt_service()
        
        stt_hebrish_service.reset_hebrish_stt_service()
        
        # After reset, module-level variable should be None
        assert stt_hebrish_service._hebrish_stt_service is None


class TestHebrishSTTServiceHealth:
    """Test health status functionality"""

    def test_health_status_structure(self, mock_whisper_model):
        """Test health status returns correct structure"""
        stt_hebrish_service.reset_hebrish_stt_service()
        service = stt_hebrish_service.get_hebrish_stt_service()
        
        status = service.get_health_status()
        
        assert "available" in status
        assert "device" in status
        assert "model" in status
        assert isinstance(status["available"], bool)
        
        stt_hebrish_service.reset_hebrish_stt_service()


class TestHebrishSTTTranscribe:
    """Test transcription logic and progress updates"""

    @pytest.mark.asyncio
    @patch("os.getenv")
    async def test_transcribe_with_progress_local_fallback(self, mock_getenv, mock_whisper_model, mock_session_manager):
        """Test transcribe method sends progress updates (Local Fallback)"""
        # Ensure no Groq key
        mock_getenv.return_value = None
        
        # Setup mocks
        mock_instance = mock_whisper_model.return_value
        stt_hebrish_service.reset_hebrish_stt_service()
        service = stt_hebrish_service.get_hebrish_stt_service()
        
        # Mock session manager instance
        mock_sm_instance = MagicMock()
        mock_session_manager.return_value = mock_sm_instance
        
        # Mock segments and info
        MockSegment = MagicMock
        segments = [
            MockSegment(start=0.0, end=10.0, text="Hello", avg_logprob=-0.5),
            MockSegment(start=10.0, end=25.0, text="World", avg_logprob=-0.2), # > 10s gap
            MockSegment(start=25.0, end=30.0, text="!", avg_logprob=-0.1)
        ]
        mock_info = MagicMock(duration=100.0) # 100s audio
        
        # Configure transcribe return
        mock_instance.transcribe.return_value = (iter(segments), mock_info)
        
        # Execute
        result = await service.transcribe("dummy_audio.wav", task_id="task_123")
        
        # Assertions
        assert len(result.segments) == 3
        
        # Check progress calls
        # 1. Loading model (40%)
        mock_sm_instance.update_progress.assert_any_call("task_123", "Loading Whisper model...", 40)
        
        # 2. Starting (42%)
        # The code uses key timestamps and exact strings: "Transcribing: {int(seg.end)}s/{int(duration)}s"
        # Wait, the code says: session_manager.update_progress(task_id, f"Transcribing: {int(seg.end)}s/{int(duration)}s", pct)
        # But this is inside the loop.
        # The first call in the loop (seg 1, end=10): 10-0 >= 10. pct = 40 + (10/100)*20 = 42. msg = "Transcribing: 10s/100s"
        mock_sm_instance.update_progress.assert_any_call("task_123", "Transcribing: 10s/100s", 42)
        
        # 3. Intermediate update for segment 2 (end=25.0s)
        # Progress = 40 + int((25/100)*20) = 40 + 5 = 45%
        mock_sm_instance.update_progress.assert_any_call("task_123", "Transcribing: 25s/100s", 45)
        
        # 4. Final (60%)
        mock_sm_instance.update_progress.assert_any_call("task_123", "Transcription complete!", 60)


    @pytest.mark.asyncio
    @patch("app.services.stt_hebrish_service.Groq")
    @patch("os.getenv")
    async def test_transcribe_provider_selection(self, mock_getenv, mock_groq_class, mock_whisper_model, mock_session_manager):
        """Test provider selection logic"""
        # Mock env to return a key
        mock_getenv.side_effect = lambda key: "fake_msg" if key == "GROQ_API_KEY" else None
        
        service = stt_hebrish_service.get_hebrish_stt_service()
        mock_client = mock_groq_class.return_value
        
        # 1. Test "groq" -> Uses Groq
        with patch("builtins.open", new_callable=MagicMock):
            # Try to mock the async behavior of groq client if needed, or if it's run_in_threadpool it might just work if we mock the sync method it wraps?
            # The service calls: response = await run_in_threadpool(_call_groq)
            # _call_groq calls client.audio.transcriptions.create
            
            # Setup mock for groq response
            mock_groq_resp = MagicMock()
            mock_groq_resp.segments = []
            mock_client.audio.transcriptions.create.return_value = mock_groq_resp
            
            await service.transcribe("dummy.wav", provider="groq")
            mock_client.audio.transcriptions.create.assert_called()
        
        mock_client.reset_mock()
        
        # 2. Test "google" -> Uses Local (skips Groq)
        # We need to mock the local model transcribe distinctively
        mock_local_transcribe = mock_whisper_model.return_value.transcribe
        mock_local_transcribe.return_value = (iter([]), MagicMock(duration=1.0))
        
        await service.transcribe("dummy.wav", provider="google")
        mock_client.audio.transcriptions.create.assert_not_called()
        mock_local_transcribe.assert_called()
        
        mock_client.reset_mock()
        mock_local_transcribe.reset_mock()
        
        # 3. Test "auto" with key -> Uses Groq
        with patch("builtins.open", new_callable=MagicMock):
            mock_groq_resp = MagicMock()
            mock_groq_resp.segments = []
            mock_client.audio.transcriptions.create.return_value = mock_groq_resp
            
            await service.transcribe("dummy.wav", provider="auto")
            mock_client.audio.transcriptions.create.assert_called()
