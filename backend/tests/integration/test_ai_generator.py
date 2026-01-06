"""Integration tests for AI Generator"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


class TestAIGenerator:
    """Test the AI Generator service with mocks"""

    @pytest.fixture
    def mock_generative_model(self):
        with patch("google.generativeai.GenerativeModel") as mock:
            yield mock

    @patch("app.services.ai_generator.genai.get_file")
    @patch("app.services.ai_generator.genai.upload_file")
    @patch("app.services.ai_generator.genai.GenerativeModel")
    def test_analyze_audio_relevance(self, mock_model_class, mock_upload, mock_get_file):
        from app.services.ai_generator import DocumentationGenerator
        
        # Setup mock file upload
        mock_file = MagicMock()
        mock_file.state.name = "ACTIVE"
        mock_file.name = "test_file"
        mock_upload.return_value = mock_file
        mock_get_file.return_value = mock_file
        
        # Setup mock model response
        mock_model = mock_model_class.return_value
        mock_response = MagicMock()
        mock_response.text = '{"relevant_segments": [{"start": 1.0, "end": 5.0, "reason": "test"}]}'
        mock_model.generate_content.return_value = mock_response
        
        generator = DocumentationGenerator()
        result = generator.analyze_video_relevance(
            video_path=str(Path("test.wav")),
            context_keywords=["test"]
        )
        
        # analyze_video_relevance returns a list of segments directly
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["start"] == 1.0
        assert result[0]["end"] == 5.0

    @patch("app.services.ai_generator.genai.upload_file")
    @patch("app.services.ai_generator.genai.GenerativeModel")
    def test_generate_documentation(self, mock_model_class, mock_upload):
        from app.services.ai_generator import DocumentationGenerator
        from app.services.prompt_loader import PromptConfig
        
        # Setup mock file upload
        mock_file = MagicMock()
        mock_upload.return_value = mock_file
        
        # Setup mock model response
        mock_model = mock_model_class.return_value
        mock_response = MagicMock()
        mock_response.text = "# Generated Documentation Content"
        mock_model.generate_content.return_value = mock_response
        
        config = PromptConfig(
            name="Test",
            description="Test",
            system_instruction="Test Instruction",
            department="R&D"
        )
        
        generator = DocumentationGenerator()
        result = generator.generate_documentation(
            frame_paths=[str(Path("f1.jpg"))],
            prompt_config=config,
            audio_transcript="test transcript"
        )
        
        assert result == "# Generated Documentation Content"
        assert mock_model.generate_content.called

